# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2022 quarz12
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program. If not, see <http://www.gnu.org/licenses/>.

import concurrent.futures
import requests
import json
from bs4 import BeautifulSoup as BS  # requirement
from typing import List, Optional

try:
    import cchardet #optional for better speed
except ImportError:
    pass

from cps.services.Metadata import MetaRecord, MetaSourceInfo, Metadata
import cps.logger as logger

#from time import time
from operator import itemgetter
log = logger.create()


class Aladin(Metadata):
    __name__ = "Aladin"
    __id__ = "aladin"
    headers = {'upgrade-insecure-requests': '1',
               'user-agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0',
               'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8',
               'Sec-Fetch-Site': 'same-origin',
               'Sec-Fetch-Mode': 'navigate',
               'Sec-Fetch-User': '?1',
               'Sec-Fetch-Dest': 'document',
               'Upgrade-Insecure-Requests': '1',
               'Alt-Used' : 'www.aladin.co.kr',
               'Priority' : 'u=0, i',
               'accept-encoding': 'gzip, deflate, br, zstd',
               'Referer' : 'https://www.aladin.co.kr/',
               'accept-language': 'en-US,en;q=0.9'}
    session = requests.Session()
    session.headers=headers

    def search(
        self, query: str, generic_cover: str = "", locale: str = "en"
    ) -> Optional[List[MetaRecord]]:
        def inner(link, index) -> [dict, int]:
            with self.session as session:
                try:
                    r = session.get(f"{link}")
                    r.raise_for_status()
                except Exception as ex:
                    log.warning(ex)
                    return []
                long_soup = BS(r.text, "lxml")
                soup2 = long_soup.find("div", attrs={"cel_widget_id": "dpx-ppd_csm_instrumentation_wrapper"})
                script_tag = long_soup.findAll("script", attrs={"type":"application/ld+json"})[0]
                if script_tag:
                    try:
                        json_text = script_tag.string or script_tag.text
                        data = json.loads(json_text)

                        match = MetaRecord(
                            id = link.split("ItemId=")[-1],
                            title = data.get("name", "").replace(" (Paperback)", ""),
                            authors = [item.strip() for item in data.get("author", {}).get("name", "").split(",")],
                            source=MetaSourceInfo(
                                id=self.__id__,
                                description="Aladin Books",
                                link="https://aladin.co.kr/"
                            ),
                            url = f"{link}",
                            publisher= data.get("publisher", {}).get("name"),
                            publishedDate= data.get("workExample", [{}])[0].get("datePublished"),
                            tags = [item.strip() for item in data.get("genre","").split(",")],
                            cover = data.get("image"),
                            description = data.get("description"),
                        )

                        try:
                            match.rating = int(data.get("aggregateRating", {}).get("ratingValue"))
                        except (AttributeError, TypeError, ValueError):
                            match.rating = 0

                        match.identifiers = {"aladin.co.kr": match.id}
                        match.identifiers["isbn"] = data.get("workExample", [{}])[0].get("isbn")

                        # 소개 페이지 따로 하자
                        #match.description = "aaaaa"
                        match.description = self._parse_description(match.identifiers["isbn"]) or match.description

                        return match, index
                    except Exception as e:
                        log.error_or_exception(e)
                        return []

        val = list()
        if self.active:
            try:
                results = self.session.get(
                    f"https://www.aladin.co.kr/search/wsearchresult.aspx?SearchTarget=All&SearchWord={query.replace(' ', '+')}",
                    headers=self.headers)

                results.raise_for_status()
            except requests.exceptions.HTTPError as e:
                log.error_or_exception(e)
                return []
            except Exception as e:
                log.warning(e)
                return []
            soup = BS(results.text, 'html.parser')

            ## List Comprehension은 보기가 너무 어렵다.
            #links_list = [next(filter(lambda i: "wproduct" in i["href"], x.findAll("a", attrs={"class": "bo3"})), None)["href"] for x in
            #              soup.findAll("div", attrs={"class": "ss_book_list"})]
            links_list = []
            for x in soup.findAll("div", attrs={"class": "ss_book_list"}):
                a_tags = x.findAll("a", attrs={"class": "bo3"})
                link_tag = next((i for i in a_tags if "wproduct" in i.get("href", "")), None)
                if link_tag:
                    links_list.append(link_tag["href"])

            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                fut = {executor.submit(inner, link, index) for index, link in enumerate(links_list[:5])}
                val = list(map(lambda x : x.result(), concurrent.futures.as_completed(fut)))
        result = list(filter(lambda x: x, val))

        return [x[0] for x in sorted(result, key=itemgetter(1))]

    def _parse_description(self, isbn) -> str:
        # <!-- 책소개-->
        # aladin uses other request for description and toc.
        # 국내 도서 : 책소개
        # http://www.aladin.co.kr/shop/product/getContents.aspx?ISBN=8970122648&name=Introduce&type=0&date=16
        # 외국 도서 : 출판사 제공 책소개"
        # https://www.aladin.co.kr/shop/product/getContents.aspx?ISBN=1491919531&name=PublisherDesc&type=0&date=15
        description = ""
        with self.session as session:
            try:
                r = session.get(f"http://www.aladin.co.kr/shop/product/getContents.aspx?ISBN={isbn}&name=Introduce&type=0&date={datetime.datetime.now().hour}")
                r.raise_for_status()
            except Exception as ex:
                log.warning(ex)
                return []
            soup = BS(r.text, "html.parser")
            introduce_text = ' '.join(
                div.get_text(strip=True) for div in soup.find("div", class_="Ere_prod_mconts_box").find_all("div", class_="Ere_prod_mconts_R")
            ) if soup.find("div", class_="Ere_prod_mconts_box") else ""
            description = introduce_text
        return description

if __name__ == "__main__":
    aladin = Aladin()
    result = aladin.search("파이썬")
    for item in result:
        print(item)

