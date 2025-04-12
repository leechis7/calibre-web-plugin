# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2021 OzzieIsaacs
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

# Aladin Books api document
from typing import Dict, List, Optional
from urllib.parse import quote
from datetime import datetime

import requests

from cps import logger
from cps.isoLanguages import get_lang3, get_language_name
from cps.services.Metadata import MetaRecord, MetaSourceInfo, Metadata

log = logger.create()

TTB_KEY = "ttbleechis71322001"


class AladinAPI(Metadata):
    __name__ = "Aladin API"
    __id__ = "aladinapi"
    DESCRIPTION = "Aladin Books"
    META_URL = "https://www.aladin.co.kr/"
    BOOK_URL = "https://www.aladin.co.kr/shop/wproduct.aspx?ItemId="
    SEARCH_URL = (
        "https://www.aladin.co.kr/ttb/api/ItemSearch.aspx"
        f"?ttbkey={TTB_KEY}"
        "&MaxResults=5"
        "&start=1"
        "&QueryType=Title"
        "&SearchTarget=Book"
        "&output=js"
        "&Version=20131101"
        "&Query="
    )
    SEARCH_F_URL = (
        "https://www.aladin.co.kr/ttb/api/ItemSearch.aspx"
        f"?ttbkey={TTB_KEY}"
        "&MaxResults=5"
        "&start=1"
        "&QueryType=Title"
        "&SearchTarget=Foreign"
        "&output=js"
        "&Version=20131101"
        "&Query="
    )

    def search(
        self, query: str, generic_cover: str = "", locale: str = "ko"
    ) -> Optional[List[MetaRecord]]:
        val = list()
        if self.active:

            title_tokens = list(self.get_title_tokens(query, strip_joiners=False))
            if title_tokens:
                tokens = [quote(t.encode("utf-8")) for t in title_tokens]
                query = "+".join(tokens)

            # 국내도서
            try:
                results = requests.get(AladinAPI.SEARCH_URL + query)
                results.raise_for_status()
            except Exception as e:
                log.warning(e)
                return []
            for result in results.json().get("item", []):
                val.append(
                    self._parse_search_result(
                        result=result,
                        generic_cover=generic_cover,
                        locale="ko",
                        lang="kor",
                    )
                )
            # 외국도서
            try:
                results = requests.get(AladinAPI.SEARCH_F_URL + query)
                results.raise_for_status()
            except Exception as e:
                log.warning(e)
                return []
            for result in results.json().get("item", []):
                val.append(
                    self._parse_search_result(
                        result=result,
                        generic_cover=generic_cover,
                        locale="ko",
                        lang="eng",
                    )
                )
        return val

    def _parse_search_result(
        self, result: Dict, generic_cover: str, locale: str, lang: str = "kor"
    ) -> MetaRecord:
        match = MetaRecord(
            id=result["itemId"],
            title=result["title"],
            authors=[item.strip() for item in result["author"].split(",")],
            url=AladinAPI.BOOK_URL + str(result["itemId"]),
            source=MetaSourceInfo(
                id=self.__id__,
                description=AladinAPI.DESCRIPTION,
                link=AladinAPI.META_URL,
            ),
        )

        match.cover = self._parse_cover(result=result, generic_cover=generic_cover)
        match.description = result["description"]
        match.languages = lang  # self._parse_languages(result=result, locale=locale)
        match.publisher = result["publisher"]
        try:
            datetime.strptime(result["pubDate"], "%Y-%m-%d")
            match.publishedDate = result["pubDate"]
        except ValueError:
            match.publishedDate = ""
        match.rating = result["customerReviewRank"]
        try:
            match.series, match.series_index = (
                result["seriesInfo"].get("seriesName", ""),
                1,
            )
        except Exception as e:
            match.series, match.series_index = "", 1
        match.tags = ([item.strip() for item in result["categoryName"].split(",")],)

        match.identifiers = {"aladin.co.kr": match.id}
        match.identifiers["isbn"] = result["isbn13"]
        return match

    @staticmethod
    def _parse_cover(result: Dict, generic_cover: str) -> str:
        if result["cover"]:
            cover_url = result["cover"].replace("coversum", "cover500")
            return cover_url
        return generic_cover

    @staticmethod
    def _parse_languages(result: Dict, locale: str) -> List[str]:
        language_iso2 = locale
        languages = (
            [get_language_name(locale, get_lang3(language_iso2))]
            if language_iso2
            else []
        )
        return languages
