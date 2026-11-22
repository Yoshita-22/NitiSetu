import logging
from datetime import datetime, timezone
from typing import List, Optional
import httpx
from app.core.config import settings
from app.schemas.law_schemas import LawSearchResponse, LawSearchResultItem

logger = logging.getLogger("nitsetu.nyaykosh")


class NyayKoshMockAdapter:
    """Isolated development mock adapter providing verified Indian statutory provisions.

    Used for testing, local offline development, and graceful resilience when
    the upstream NeGD NyayKosh API is unreachable.
    All provisions represent real text from official Acts published in The Gazette of India.
    """

    MOCK_STATUTES: List[dict] = [
        {
            "law_name": "The Consumer Protection Act, 2019",
            "act_name": "Consumer Protection Act 2019",
            "section_number": "Section 2(9)",
            "content": (
                "'Consumer rights' includes: (i) the right to be protected against the marketing of goods, "
                "products or services which are hazardous to life and property; (ii) the right to be informed about "
                "the quality, quantity, potency, purity, standard and price of goods, products or services; "
                "(iii) the right to be assured access to a variety of goods, products or services at competitive prices; "
                "(iv) the right to be heard and assured that consumer's interests will receive due consideration; "
                "(v) the right to seek redressal against unfair trade practice or restrictive trade practices or "
                "unscrupulous exploitation of consumers; and (vi) the right to consumer awareness."
            ),
            "source_url": "https://www.indiacode.nic.in/handle/123456789/15256",
            "category": "Consumer Rights",
            "keywords": ["consumer", "rights", "refund", "defect", "unfair trade", "protection", "goods", "services"],
        },
        {
            "law_name": "The Consumer Protection Act, 2019",
            "act_name": "Consumer Protection Act 2019",
            "section_number": "Section 35",
            "content": (
                "A complaint, in relation to any goods sold or delivered or agreed to be sold or delivered or "
                "any service provided or agreed to be provided, may be filed with a District Commission by: "
                "(a) the consumer to whom such goods are sold or delivered or agreed to be sold or delivered or "
                "such service is provided or agreed to be provided; (b) any recognized consumer association; "
                "(c) one or more consumers, where there are numerous consumers having the same interest; or "
                "(d) the Central Government, the Central Authority or the State Government."
            ),
            "source_url": "https://www.indiacode.nic.in/handle/123456789/15256",
            "category": "Consumer Dispute Redressal",
            "keywords": ["complaint", "district commission", "consumer court", "filing", "dispute", "redressal"],
        },
        {
            "law_name": "The Digital Personal Data Protection Act, 2023",
            "act_name": "DPDP Act 2023",
            "section_number": "Section 6",
            "content": (
                "(1) The consent given by the Data Principal shall be free, specific, informed, unconditional and "
                "unambiguous with a clear affirmative action, and shall signify an agreement to the processing of her "
                "personal data for the specified purpose, and be limited to such personal data as is necessary for "
                "such specified purpose. (2) Any part of consent which constitutes an infringement of the provisions "
                "of this Act or the rules made thereunder shall be invalid."
            ),
            "source_url": "https://www.meity.gov.in/content/digital-personal-data-protection-act-2023",
            "category": "Data Privacy",
            "keywords": ["privacy", "data", "consent", "dpdp", "personal data", "digital rights", "meity"],
        },
        {
            "law_name": "The Digital Personal Data Protection Act, 2023",
            "act_name": "DPDP Act 2023",
            "section_number": "Section 11",
            "content": (
                "The Data Principal shall have the right to obtain from the Data Fiduciary to whom she has "
                "previously given consent for processing of personal data: (a) a summary of personal data which "
                "is being processed and the processing activities undertaken; (b) the identities of all other Data "
                "Fiduciaries with whom the personal data has been shared; and (c) any other information as prescribed."
            ),
            "source_url": "https://www.meity.gov.in/content/digital-personal-data-protection-act-2023",
            "category": "Data Privacy",
            "keywords": ["data access", "rights", "data principal", "information", "transparency", "fiduciary"],
        },
        {
            "law_name": "The Aadhaar (Targeted Delivery of Financial and Other Subsidies, Benefits and Services) Act, 2016",
            "act_name": "Aadhaar Act 2016",
            "section_number": "Section 7",
            "content": (
                "The Central Government or, as the case may be, the State Government may, for the purpose of "
                "establishing identity of an individual as a condition for receipt of a subsidy, benefit or service "
                "for which the expenditure is incurred from the Consolidated Fund of India or State, require that such "
                "individual undergo authentication, or furnish proof of possession of Aadhaar number or in the case of "
                "an individual to whom no Aadhaar number has been assigned, make an application for enrolment: "
                "Provided that if an Aadhaar number is not assigned, the individual shall be offered alternate and "
                "viable means of identification for receipt of the subsidy, benefit or service."
            ),
            "source_url": "https://uidai.gov.in/en/about-uidai/legal-framework.html",
            "category": "Identity & Subsidies",
            "keywords": ["aadhaar", "subsidy", "welfare", "benefit", "uidai", "identification", "schemes", "pattadar"],
        },
        {
            "law_name": "The Information Technology Act, 2000",
            "act_name": "Information Technology Act 2000",
            "section_number": "Section 43A",
            "content": (
                "Where a body corporate, possessing, dealing or handling any sensitive personal data or information "
                "in a computer resource which it owns, controls or operates, is negligent in implementing and maintaining "
                "reasonable security practices and procedures and thereby causes wrongful loss or wrongful gain to any person, "
                "such body corporate shall be liable to pay damages by way of compensation to the person so affected."
            ),
            "source_url": "https://www.indiacode.nic.in/handle/123456789/13116",
            "category": "Cyber & Information Technology",
            "keywords": ["cyber", "data breach", "compensation", "security", "technology", "sensitive data", "it act"],
        },
        {
            "law_name": "The Rights of Persons with Disabilities Act, 2016",
            "act_name": "RPwD Act 2016",
            "section_number": "Section 3",
            "content": (
                "(1) The appropriate Government shall ensure that the persons with disabilities enjoy the right to equality, "
                "life with dignity and respect for his or her integrity equally with others. (2) The appropriate Government "
                "shall take steps to utilize the capacity of persons with disabilities by providing appropriate environment. "
                "(3) No person with disability shall be discriminated on the ground of disability."
            ),
            "source_url": "https://www.indiacode.nic.in/handle/123456789/2155",
            "category": "Disability Rights & Equality",
            "keywords": ["disability", "equality", "discrimination", "inclusion", "rights", "divyang"],
        },
    ]

    @classmethod
    def search(cls, query: str) -> List[LawSearchResultItem]:
        """Search mock statutes based on keyword match in content or title."""
        now_iso = datetime.now(timezone.utc).isoformat()
        clean_q = query.strip().lower()

        matched = []
        for s in cls.MOCK_STATUTES:
            match_score = 0
            if clean_q in s["law_name"].lower() or clean_q in s["section_number"].lower():
                match_score += 3
            if clean_q in s["content"].lower():
                match_score += 2
            for kw in s.get("keywords", []):
                if kw in clean_q or clean_q in kw:
                    match_score += 1

            if match_score > 0:
                matched.append(
                    LawSearchResultItem(
                        law_name=s["law_name"],
                        act_name=s["act_name"],
                        section_number=s["section_number"],
                        content=s["content"],
                        source_url=s["source_url"],
                        category=s.get("category"),
                        retrieval_timestamp=now_iso,
                    )
                )

        # If no strict keyword matched, return top general provisions to assist citizen exploration
        if not matched:
            matched = [
                LawSearchResultItem(
                    law_name=s["law_name"],
                    act_name=s["act_name"],
                    section_number=s["section_number"],
                    content=s["content"],
                    source_url=s["source_url"],
                    category=s.get("category"),
                    retrieval_timestamp=now_iso,
                )
                for s in cls.MOCK_STATUTES[:3]
            ]

        return matched


class NyayKoshService:
    """Service communicating with the official NeGD NyayKosh (Law as Code) API.

    Gracefully falls back to the NyayKoshMockAdapter if the government network
    endpoint is temporarily unreachable or offline.
    """

    def __init__(self):
        self.base_url = settings.NYAYKOSH_BASE_URL.rstrip("/")
        self.timeout = settings.NYAYKOSH_TIMEOUT_SECONDS
        self.api_key = settings.NYAYKOSH_API_KEY

    async def search_laws(self, query: str) -> LawSearchResponse:
        """Search legal provisions using NyayKosh.

        Attempts live NeGD REST endpoint first. If live communication fails or
        times out, falls back to the separated mock adapter while transparently
        labeling is_live_data=False.
        """
        trimmed_query = query.strip() if query else ""
        if not trimmed_query:
            return LawSearchResponse(
                success=True,
                source="nyaykosh",
                is_live_data=False,
                query="",
                total_results=0,
                results=[],
                message="Please provide a non-empty search query.",
            )

        # 1. Attempt live API call to NeGD NyayKosh
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                endpoint = f"{self.base_url}/laws"
                params = {"q": trimmed_query}

                logger.info(f"Querying live NyayKosh API: {endpoint} with params={params}")
                response = await client.get(endpoint, params=params, headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    now_iso = datetime.now(timezone.utc).isoformat()
                    results: List[LawSearchResultItem] = []

                    # Parse official NeGD response shape
                    laws_list = data if isinstance(data, list) else data.get("data", data.get("laws", []))
                    for item in laws_list:
                        law_name = item.get("title") or item.get("law_name") or item.get("name") or "Indian Statute"
                        act_name = item.get("act_name") or law_name
                        slug = item.get("slug") or ""
                        source_url = f"https://lawascode.negd.in/laws/{slug}" if slug else "https://lawascode.negd.in"

                        # Check for nested provisions or top-level law description
                        provisions = item.get("provisions", [])
                        if provisions:
                            for prov in provisions:
                                results.append(
                                    LawSearchResultItem(
                                        law_name=law_name,
                                        act_name=act_name,
                                        section_number=prov.get("section_number") or prov.get("number") or "Section",
                                        content=prov.get("text") or prov.get("content") or prov.get("summary") or "",
                                        source_url=source_url,
                                        category=item.get("category"),
                                        retrieval_timestamp=now_iso,
                                    )
                                )
                        else:
                            content_text = item.get("description") or item.get("summary") or item.get("statement") or ""
                            results.append(
                                LawSearchResultItem(
                                    law_name=law_name,
                                    act_name=act_name,
                                    section_number=item.get("section_number", "Full Act Overview"),
                                    content=content_text,
                                    source_url=source_url,
                                    category=item.get("category"),
                                    retrieval_timestamp=now_iso,
                                )
                            )

                    if results:
                        return LawSearchResponse(
                            success=True,
                            source="nyaykosh",
                            is_live_data=True,
                            query=trimmed_query,
                            total_results=len(results),
                            results=results,
                            message="Retrieved directly from official NeGD NyayKosh API.",
                        )

        except (httpx.RequestError, httpx.HTTPStatusError, Exception) as exc:
            logger.warning(
                f"NyayKosh live API call failed ({exc.__class__.__name__}: {exc}). "
                "Engaging NyayKoshMockAdapter fallback."
            )

        # 2. Resilient fallback to verified statutory mock adapter
        mock_results = NyayKoshMockAdapter.search(trimmed_query)
        return LawSearchResponse(
            success=True,
            source="nyaykosh_mock_adapter",
            is_live_data=False,
            query=trimmed_query,
            total_results=len(mock_results),
            results=mock_results,
            message=(
                "Notice: Live NeGD NyayKosh endpoint was unreachable or returned no records; "
                "displaying verified statutory provisions from the development mock adapter."
            ),
        )


# Default singleton service
nyaykosh_service = NyayKoshService()
