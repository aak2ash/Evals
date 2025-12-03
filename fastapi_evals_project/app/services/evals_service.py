import os
import asyncio
import json
import re
import logging
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

import pandas as pd
import httpx

from app.core.config import settings
from app.services.feedback_service import FeedbackService
from app.services.transcript_client import TranscriptAnalyzerClient
from constants import BASE_TEMPLATE

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def parse_transcript(raw: Optional[str]) -> List[Dict[str, str]]:
    if not isinstance(raw, str):
        return []
    messages = []
    for line in raw.split("\n"):
        m = re.match(r"(assistant|user):\s*(.*)", line.strip(), re.IGNORECASE)
        if not m:
            continue
        role = m.group(1).lower()
        messages.append({"role": role, "content": m.group(2)})
    return messages


def parse_lead_data(raw: Optional[str]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    if raw is None:
        return result
    try:
        if pd.isna(raw):
            return result
    except Exception:
        pass
    for line in str(raw).split("\n"):
        if ":" in line:
            k, v = line.split(":", 1)
            result[k.strip()] = v.strip()
    return result


class EvalsService:
    """
    Orchestrates:
      - reading excel (async via threadpool)
      - building payload
      - calling transcript analyzer
      - calling OpenAI judge
      - appending to DataFrame
      - saving final Excel into project outputs/
    """

    def __init__(
        self,
        transcript_client: Optional[TranscriptAnalyzerClient] = None,
        feedback_client: Optional[FeedbackService] = None,
        max_workers: Optional[int] = None,
        concurrency: Optional[int] = 1,
    ):
        self._executor = ThreadPoolExecutor(max_workers or settings.max_workers)
        self.transcript_client = transcript_client or TranscriptAnalyzerClient()
        self.feedback_client = feedback_client or FeedbackService()
        self.PROJECT_ROOT = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        self.OUTPUT_DIR = os.path.join(self.PROJECT_ROOT, "outputs")
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)
        self._concurrency = concurrency or 1
        self._sem = asyncio.Semaphore(self._concurrency)

    async def _read_excel(self, path: str) -> pd.DataFrame:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, lambda: pd.read_excel(path))

    async def _save_excel(self, df: pd.DataFrame, filename: str) -> str:
        loop = asyncio.get_running_loop()
        output_path = os.path.join(self.OUTPUT_DIR, filename)
        await loop.run_in_executor(
            self._executor, lambda: df.to_excel(output_path, index=False)
        )
        return output_path

    def _build_payload_from_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        payload = deepcopy(BASE_TEMPLATE)
        ld = parse_lead_data(row.get("lead_data", ""))
        print(ld)
        client_code = row.get("client_code", "")
        for k, v in ld.items():
            if k in payload["lead_data"]:
                print(k)
                payload["lead_data"][k] = v
                if k == 'university_name':
                    payload["lead_data"]["university"]["id"] = None
                    payload["lead_data"]["university"]["name"] = v
                    continue
                if k == 'destination_country_name':
                    print("reached here")
                    payload["lead_data"]["destination_country"]["id"] = None
                    payload["lead_data"]["destination_country"]["name"] = v
                    continue
                if k == 'destination_city_name':
                    payload["lead_data"]["destination_city"]["id"] = None
                    continue
                if k == 'budget_duration':
                    payload["lead_data"]["budget"]["duration"] = v
                    continue
                if k == 'budget_currency':
                    payload['lead_data']['budget']['currency'] = v
                    continue
                if k == 'min_budget':
                    payload['lead_data']['budget']['min_budget'] = v
                    continue
                if k == 'max_budget':
                    payload['lead_data']['budget']['max_budget'] = v
                    continue
                if k == 'lease_unit':
                    payload['lead_data']['lease']['unit'] = v
                if k == 'lease_value':
                    payload['lead_data']['lease']['value'] = v
                    continue
        print(payload)
        exit()
        payload["transcript"] = parse_transcript(row.get("transcript", "") or "")
        payload["latest_message"] = {
            "channel": "widget",
            "text": row.get("latest_message", "") or "",
        }
        payload["client_details"]["client_code"] = client_code
        return payload

    async def evaluate_row(self, row: pd.Series) -> Dict[str, Any]:
        out: Dict[str, Any] = {"predicted_output": None, "judge": None, "error": None}
        try:
            payload = self._build_payload_from_row(row.to_dict())
            ta_resp = await self.transcript_client.analyze_transcript(payload)
            predicted_text = ""
            try:
                if isinstance(ta_resp, dict):
                    cr = ta_resp.get("channel_response", [])
                    if isinstance(cr, list) and len(cr) > 0:
                        predicted_text = cr[0].get("text", "") or ""
                    else:
                        predicted_text = (
                            ta_resp.get("text") or ta_resp.get("message") or ""
                        )
                elif isinstance(ta_resp, str):
                    predicted_text = ta_resp
            except Exception:
                predicted_text = ""

            out["predicted_output"] = predicted_text

            async with self._sem:
                expected = str(row.get("expected_output", "") or "")
                transcript_raw = row.get("transcript", "") or ""
                judge_resp = await self.feedback_client.score(
                    expected=expected,
                    predicted=predicted_text,
                    transcript=transcript_raw,
                )
                out["judge"] = judge_resp

            return out
        except Exception as e:
            logger.exception("Error evaluating row: %s", e)
            out["error"] = str(e)
            return out

    async def process_excel(
        self, input_path: str, output_filename: Optional[str] = None
    ) -> str:
        df = await self._read_excel(input_path)
        df["predicted_output"] = None
        df["eval_reasoning"] = None
        df["score_accuracy"] = None
        df["score_completeness"] = None
        df["score_relevance"] = None
        df["score_overall"] = None
        df["differences"] = None
        df["pass_fail"] = None
        df["judge_raw"] = None
        df["eval_error"] = None

        for idx, row in df.iterrows():
            res = await self.evaluate_row(row)
            if res.get("error"):
                df.at[idx, "eval_error"] = res["error"]
                continue
            predicted = res.get("predicted_output", "")
            df.at[idx, "predicted_output"] = predicted
            judge = res.get("judge")
            df.at[idx, "judge_raw"] = judge

            if isinstance(judge, dict):
                df.at[idx, "eval_reasoning"] = judge.get("reasoning") or judge.get(
                    "reason"
                )
                df.at[idx, "score_accuracy"] = judge.get("accuracy")
                df.at[idx, "score_completeness"] = judge.get("completeness")
                df.at[idx, "score_relevance"] = judge.get("relevance")
                df.at[idx, "score_overall"] = judge.get("overall")
                diffs = judge.get("differences")
                try:
                    if diffs and not isinstance(diffs, str):
                        df.at[idx, "differences"] = json.dumps(diffs)
                    else:
                        df.at[idx, "differences"] = diffs
                except Exception:
                    df.at[idx, "differences"] = str(diffs)
                df.at[idx, "pass_fail"] = judge.get("pass_fail")
            else:
                df.at[idx, "eval_reasoning"] = None
                df.at[idx, "eval_error"] = (
                    json.dumps(judge) if judge is not None else None
                )

        if not output_filename:
            base, _ = os.path.splitext(os.path.basename(input_path))
            output_filename = f"{base}_evaluated.xlsx"

        output_path = await self._save_excel(df, output_filename)
        return output_path

    async def close(self):
        try:
            await self.transcript_client.close()
        except Exception:
            pass
        try:
            await self.feedback_client.close()
        except Exception:
            pass
