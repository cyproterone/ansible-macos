#!/usr/local/bin/python3

from argparse import ArgumentParser, Namespace
from asyncio import gather, get_running_loop, run
from datetime import datetime
from json import loads
from os.path import isfile, join, realpath, splitext
from typing import Any, Sequence, Set, Tuple
from urllib.parse import parse_qs, urlparse
from urllib.request import urlopen


async def get(uri: str) -> bytes:
    def get():
        with urlopen(uri) as fd:
            return fd.read()

    loop = get_running_loop()
    res = await loop.run_in_executor(None, get)
    return res


def write(data: bytes, path: str) -> None:
    real_path = realpath(path)
    with open(real_path, "wb") as fd:
        fd.write(data)


def sanitize(
    path: str, replace: str = "_", safe_chars: Set[str] = {" ", ".", "_"}
) -> str:
    sanitized = (c if c.isalnum() or c in safe_chars else replace for c in path)
    return "".join(sanitized).rstrip()


def extract(partial: Any) -> Tuple[str, str]:
    uri = f"https://www.bing.com/{partial['url']}"
    title = partial["title"]
    date = datetime.strptime(partial["startdate"], "%Y%m%d")
    formatted_date = date.strftime("%Y_%m_%d")
    query = urlparse(uri).query
    file_name = parse_qs(query)["id"][0]
    _, ext = splitext(file_name)
    filename = sanitize(f"{formatted_date} {title}{ext}")
    return uri, filename


async def bing(count=1) -> Sequence[Tuple[str, str]]:
    uri = f"https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n={count}"
    res = await get(uri)
    hist = loads(res.decode())
    images = tuple(extract(i) for i in hist["images"])
    return images


def parse_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument("-o", "--out", required=True)
    parser.add_argument("-d", "--days", type=int, default=1)
    return parser.parse_args()


async def main() -> None:
    print(f"-- | {datetime.now()} | --")
    args = parse_args()
    base_path = realpath(args.out)
    images = await bing(args.days)
    candidates = tuple(
        (uri, filename)
        for uri, filename in images
        if not isfile(join(base_path, filename))
    )
    futures = (get(uri) for uri, _ in candidates)
    res = await gather(*futures)
    for data, (_, filename) in zip(res, candidates):
        path = join(base_path, filename)
        write(data, path)


if __name__ == "__main__":
    run(main())
