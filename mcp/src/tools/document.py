from typing import Dict, Optional, List, Union
import logging
import json
import re

from fastmcp import FastMCP

class DocumentTools:
    def __init__(self, search_client, logger: Optional[logging.Logger] = None):
        self.search_client = search_client
        self.logger = logger or logging.getLogger(__name__)
    
    def register_tools(self, mcp: FastMCP):

    
        @mcp.tool()
        def search_chinataxcenter(
            index: str = "chinataxcenter_new",
            query_text: Optional[str] = None,
            from_: int = 0,
            category: str = None,
            size: int = 10,
            date_from: Optional[str] = None,
            date_to: Optional[str] = None,
            issuing_body: Optional[str] = None,
            effectiveness: Optional[str] = None,
            tax_type: Optional[str] = None,
            circular_no: Optional[Union[str, List[str]]] = None,
            sort_field: Optional[str] = None,
            sort_order: str = "desc",
        ) -> str:
            """
            Search the 'chinataxcenter_new' index with common filters.

            Args:
                query_text: Full-text terms matched against title/content/topic. If passed as a string
                    representation of an array (e.g., '["词1","词2"]') or a comma/space-separated
                    list (e.g., '词1, 词2' or '词1 词2'), it will be split into multiple terms and all
                    terms must match (AND semantics).
                from_: Pagination start offset
                size: Page size
                date_from: Lower bound for publishedDate (e.g., '2012-01-01')
                date_to: Upper bound for publishedDate (e.g., '2013-01-01')
                issuing_body: Match on issuingBody
                effectiveness: Match on effectiveness (default '有效')
                tax_type: Match on taxType
                circular_no: Match on one or more circularNo values (document circular number). Accepts
                    a string, JSON array string, or list of strings.
                sort_field: Field to sort by; default None to use _score ordering
                sort_order: 'asc' or 'desc' (default 'desc'); used only if sort_field is set

            Curl example (adjust index/filters as needed):
                curl -u "elastic:changeme" -H 'Content-Type: application/json' -X POST \
                "http://localhost:9200/chinataxcenter_new/_search" -d '{
                  "from": 0,
                  "size": 10,
                  "query": {
                    "bool": {
                      "must": [
                        { "multi_match": { "query": "税务 政策", "fields": ["title","content"], "operator": "or", "fuzziness": "AUTO" } }
                      ],
                      "filter": [
                        { "match": { "effectiveness": "有效" } },
                        { "match": { "issuingBody": "国家税务总局" } },
                        { "match": { "taxType": "增值税" } },
                        { "range": { "publishedDate": { "gte": "2024-01-01", "lte": "2025-12-31" } } }
                      ]
                    }
                }
                }'
            """

            must: List[Dict] = []
            filters: List[Dict] = []

            # Log incoming parameters for debugging
            try:
                self.logger.info(
                    "search_chinataxcenter params | index=%s from_=%s size=%s date_from=%s date_to=%s issuing_body=%s effectiveness=%s tax_type=%s circular_no=%s sort=%s:%s",
                    index, from_, size, date_from, date_to, issuing_body, effectiveness, tax_type, circular_no, sort_field, sort_order,
                )
            except Exception:
                pass
#===============================================================================================
#=====================================  query_text  ============================================
#===============================================================================================
            self.logger.info(f"search_chinataxcenter raw query_text: {query_text}")
            if query_text:
                terms: List[str] = []
                # Try to parse JSON array first
                try:
                    parsed = json.loads(query_text)
                    if isinstance(parsed, list):
                        terms = [str(item).strip() for item in parsed if str(item).strip()]
                except Exception:
                    pass
                # Fallbacks: comma/semicolon or whitespace separated
                if not terms:
                    raw = query_text.strip()
                    if any(sep in raw for sep in [",", "，", ";", "；"]):
                        normalized = raw.replace("；", ";").replace("，", ",")
                        parts = [p.strip() for p in normalized.replace(";", ",").split(",")]
                        terms = [p for p in parts if p]
                    else:
                        parts = [p.strip() for p in raw.split()]
                        terms = [p for p in parts if p]

                # Log parsed terms
                try:
                    self.logger.info("parsed terms (%s): %s", len(terms), terms)
                except Exception:
                    pass

                for term in terms:
                    must.append({
                        "multi_match": {
                            "query": term,
                            "fields": ["title^10", "content"],  # title 字段权重是 content 的 10 倍
                            "operator": "or",
                            "fuzziness": "AUTO",
                        }
                    })
#===============================================================================================
#=====================================  Filter  ============================================
#===============================================================================================
            if date_from or date_to:
                range_filter: Dict = {"range": {"publishedDate": {}}}
                if date_from:
                    range_filter["range"]["publishedDate"]["gte"] = date_from
                if date_to:
                    range_filter["range"]["publishedDate"]["lte"] = date_to
                filters.append(range_filter)

            if issuing_body:
                filters.append({"match": {"issuingBody": issuing_body}})

            if effectiveness:
                filters.append({"match_phrase": {"effectiveness": effectiveness}})

            if tax_type:
                filters.append({"match": {"taxType": tax_type}})
#===============================================================================================
#=====================================  circular_no  ============================================
#===============================================================================================
            circular_numbers: List[str] = []
            circular_param_supplied = circular_no is not None
            if circular_param_supplied:
                if isinstance(circular_no, str):
                    raw_circular = circular_no.strip()
                    if raw_circular:
                        parsed_circular = None
                        try:
                            parsed_circular = json.loads(raw_circular)
                        except Exception:
                            parsed_circular = None
                        if isinstance(parsed_circular, list):
                            circular_numbers = [
                                str(item).strip()
                                for item in parsed_circular
                                if str(item).strip()
                            ]
                        else:
                            # Allow comma/semicolon separated strings
                            if any(sep in raw_circular for sep in [",", "，", ";", "；"]):
                                normalized = raw_circular.replace("；", ";").replace("，", ",")
                                parts = [
                                    p.strip()
                                    for p in normalized.replace(";", ",").split(",")
                                ]
                                circular_numbers = [p for p in parts if p]
                            else:
                                circular_numbers = [raw_circular]
                elif isinstance(circular_no, (list, tuple, set)):
                    circular_numbers = [
                        str(item).strip() for item in circular_no if str(item).strip()
                    ]

            result: Dict = {
                "took": 0,
                "timed_out": False,
                "_shards": {"total": 0, "successful": 0, "skipped": 0, "failed": 0},
                "hits": {"total": {"value": 0, "relation": "eq"}, "max_score": None, "hits": []},
            }
            skip_es_search = False

            if circular_param_supplied and not circular_numbers:
                try:
                    self.logger.info(
                        "circular_no provided but empty after normalization; returning empty result"
                    )
                except Exception:
                    pass
                skip_es_search = True

            if circular_numbers:
                try:
                    self.logger.info(
                        "circular_no filters (%s): %s",
                        len(circular_numbers),
                        circular_numbers,
                    )
                except Exception:
                    pass
                filters.append(
                    {
                        "bool": {
                            "should": [
                                {"match_phrase": {"circularNo": value}}
                                for value in circular_numbers
                            ],
                            "minimum_should_match": 1,
                        }
                    }
                )

            if category:
                filters.append({"match": {"from": category}})


            # Log filters detail
            try:
                self.logger.info("filters count=%s detail=%s", len(filters), json.dumps(filters, ensure_ascii=False))
            except Exception:
                pass
#===============================================================================================
#=====================================  排序+执行搜索  ==========================================
#===============================================================================================
            if not skip_es_search:
                query: Dict = {"bool": {}}
                if must:
                    query["bool"]["must"] = must
                if filters:
                    query["bool"]["filter"] = filters
                if not must and not filters:
                    query = {"match_all": {}}

                body: Dict = {
                    "from": max(from_, 0),
                    "size": max(size, 1),
                    "query": query,
                }

                # Determine if there are query conditions (excluding default effectiveness)
                has_query_conditions = (
                    bool(query_text) or
                    bool(date_from) or
                    bool(date_to) or
                    bool(issuing_body) or
                    bool(tax_type) or
                    bool(circular_numbers) or
                    (effectiveness and effectiveness != "有效")
                )

                # If sort_field is explicitly provided, use it
                if sort_field:
                    body["sort"] = [{sort_field: {"order": sort_order}}]
                else:
                    # Apply sorting logic based on query conditions
                    # If no query conditions (or only From parameter), use simple sorting
                    if not has_query_conditions:
                        # law 排在最前面（orderFrom == 1）
                        body["sort"] = [
                            {"orderFrom ": {"order": "asc"}},  # Note: space after "orderFrom"
                            {"_score": {"order": "desc"}},
                            {"publishedDate": {"order": "desc"}},
                        ]
                    else:
                        # Complex sorting when query conditions exist
                        body["sort"] = [
                            {"orderFrom ": {"order": "asc"}},  # Note: space after "orderFrom"
                            {"_score": {"order": "desc"}},
                            {"orderIndexEffectiveness": {"order": "desc"}},
                            {"orderIndexLocation": {"order": "desc"}},
                            {"titleKeyWord": {"order": "desc"}},
                            {"titleCountFrom": {"order": "asc"}},
                            {"orderIssuingBody": {"order": "desc"}},
                            # law 排在最前面
                            {"publishedDate": {"order": "desc"}},
                        ]

                # Log final body (trimmed if large)
                try:
                    body_json = json.dumps(body, ensure_ascii=False)
                    self.logger.info("es search body (index=%s): %s", index, body_json[:2000])
                except Exception:
                    pass
#========================================执行搜索===================================================
                response = self.search_client.search_documents(index=index, body=body)
                if hasattr(response, "body"):
                    result = response.body  # type: ignore[assignment]
                else:
                    result = response  # type: ignore[assignment]

#===============================================================================================
#=====================================  circular_no 二次核对  ===================================
#===============================================================================================
                # Post-filter to enforce exact circular number matching
                if circular_numbers:
                    raw_hits = result.get("hits", {}).get("hits", []) or []
                    filtered_hits: List[Dict] = []
                    for hit in raw_hits:
                        source = hit.get("_source", {}) or {}
                        circular_field = source.get("circularNo")
                        match_exact = False
                        if isinstance(circular_field, (list, tuple, set)):
                            for item in circular_field:
                                if item is not None and str(item) in circular_numbers:
                                    match_exact = True
                                    break
                        elif circular_field is not None:
                            match_exact = str(circular_field) in circular_numbers

                        if match_exact:
                            filtered_hits.append(hit)

                    if filtered_hits != raw_hits:
                        result["hits"] = {
                            "total": len(filtered_hits),
                            "max_score": result.get("hits", {}).get("max_score"),
                            "hits": filtered_hits,
                        }

            # Log ES response summary
            try:
                total_value = (
                    result.get("hits", {}).get("total", {}).get("value")
                    if isinstance(result.get("hits", {}).get("total"), dict)
                    else result.get("hits", {}).get("total")
                )
                took = result.get("took")
                self.logger.info("es response summary | took=%s total=%s", took, total_value)
                # Preview first hit key fields
                preview = None
                if result.get("hits", {}).get("hits"):
                    h = result["hits"]["hits"][0]
                    src = h.get("_source", {})
                    preview = {
                        "_id": h.get("_id"),
                        "title": str(src.get("title", ""))[:80],
                        "topic": src.get("topic"),
                        "taxType": src.get("taxType"),
                        "issuingBody": src.get("issuingBody"),
                        "effectiveness": src.get("effectiveness"),
                        "publishedDate": src.get("publishedDate"),
                    }
                self.logger.info("first hit preview: %s", json.dumps(preview, ensure_ascii=False))
            except Exception:
                pass
#===============================================================================================
#=====================================  内容清洗、返回  ============================================
#===============================================================================================
            for hit in result['hits']['hits']:
                hit_source = hit.get('_source', {}) or {}
                hit_source['content'] = _clean_text(hit_source.get('content'))
                title = hit_source.get('title')
                effectiveness_val = hit_source.get('effectiveness')
                if isinstance(title, str):
                    if effectiveness_val and isinstance(effectiveness_val, str):
                        suffix = f" ({effectiveness_val})"
                        if suffix not in title:
                            hit_source['title'] = title + suffix
            # Clean unwanted escape sequences from text fields in the response            
            if isinstance(result, (dict, list)):
                final_output = json.dumps(result, ensure_ascii=False)
            else:
                final_output = result
            return final_output





        # @mcp.tool()
        # def build_chinataxcenter_urls(
        #     document_titles: Union[str, List[str]],
        #     index: str = "chinataxcenter_new",
        #     base_url: str = "https://tac.ey.net/",
        # ) -> str:
        #     """Generate Markdown links for chinataxcenter documents by title.

        #     Args:
        #         document_titles: Document titles to resolve. Accepts a JSON array string,
        #             comma/semicolon separated string, or a list of strings.
        #         index: Target index name (default: 'chinataxcenter_new').
        #         base_url: Base URL used to compose links for known document sources.
        #     """
        #     self.logger.info(
        #         "build_chinataxcenter_urls params | index=%s titles=%s base_url=%s",
        #         index,
        #         document_titles,
        #         base_url,
        #     )

        #     normalized_titles: List[str] = []

        #     def _extend_from_iterable(values: List[str]) -> None:
        #         for value in values:
        #             if isinstance(value, str):
        #                 trimmed = value.strip()
        #                 if trimmed:
        #                     normalized_titles.append(trimmed)

        #     if isinstance(document_titles, list):
        #         _extend_from_iterable(document_titles)
        #     elif isinstance(document_titles, str):
        #         raw_titles = document_titles.strip()
        #         parsed_titles: Optional[List[str]] = None
        #         if raw_titles:
        #             try:
        #                 parsed = json.loads(raw_titles)
        #                 if isinstance(parsed, list):
        #                     parsed_titles = [str(item) for item in parsed]
        #             except Exception:
        #                 parsed_titles = None

        #             if parsed_titles is not None:
        #                 _extend_from_iterable(parsed_titles)
        #             else:
        #                 if any(sep in raw_titles for sep in [",", "，", ";", "；"]):
        #                     normalized = raw_titles.replace("；", ";").replace("，", ",")
        #                     parts = [
        #                         p.strip()
        #                         for p in normalized.replace(";", ",").split(",")
        #                     ]
        #                     _extend_from_iterable(parts)
        #                 else:
        #                     _extend_from_iterable(raw_titles.split())
        #     else:
        #         self.logger.warning(
        #             "build_chinataxcenter_urls received unsupported type: %s",
        #             type(document_titles),
        #         )
        #     # Preserve input order while removing duplicates
        #     seen: set[str] = set()
        #     ordered_titles: List[str] = []
        #     for title in normalized_titles:
        #         if title not in seen:
        #             seen.add(title)
        #             ordered_titles.append(title)

        #     if not ordered_titles:
        #         return ""

        #     def _strip_effectiveness_suffix(title: str) -> str:
        #         match = re.match(r"^(.*)\s*\([\u4e00-\u9fa5A-Za-z0-9_]+\)\s*$", title)
        #         return match.group(1).strip() if match else title

        #     url_suffix_map = {
        #         "ChinaTaxLaw": "law/view?ID={id}",
        #         "ChinaTaxPortal": "portal/view?ID={id}",
        #         "ChinaTaxAlert": "alert/view?ID={id}",
        #     }

        #     base = base_url.rstrip("/") + "/"
        #     markdown_links: List[str] = []

        #     for raw_title in ordered_titles:
        #         title_candidate = _strip_effectiveness_suffix(raw_title)
        #         phrase_queries: List[Dict[str, Dict[str, Dict[str, Union[str, int]]]]] = [
        #             {
        #                 "match_phrase": {
        #                     "title": {
        #                         "query": title_candidate,
        #                         "slop": 0,
        #                     }
        #                 }
        #             }
        #         ]
        #         if raw_title != title_candidate:
        #             phrase_queries.append(
        #                 {
        #                     "match_phrase": {
        #                         "title": {
        #                             "query": raw_title,
        #                             "slop": 0,
        #                         }
        #                     }
        #                 }
        #             )

        #         search_body: Dict = {
        #             "size": 1,
        #             "query": {
        #                 "bool": {
        #                     "should": phrase_queries
        #                     + [
        #                         {
        #                             "match": {
        #                                 "title": {
        #                                     "query": title_candidate,
        #                                     "operator": "and",
        #                                 }
        #                             }
        #                         }
        #                     ],
        #                     "minimum_should_match": 1,
        #                     "filter": [
        #                         {
        #                             "match_phrase": {
        #                                 "effectiveness": "有效"
        #                             }
        #                         }
        #                     ],
        #                 }
        #             },
        #             "sort": [
        #                 {"orderFrom ": {"order": "asc"}},
        #                 {"_score": {"order": "desc"}},
        #                 {"publishedDate": {"order": "desc"}},
        #             ],
        #         }

        #         response = self.search_client.search_documents(
        #             index=index, body=search_body
        #         )
        #         hits: List[Dict] = response.get("hits", {}).get("hits", []) or []

        #         if not hits:
        #             self.logger.warning(
        #                 "build_chinataxcenter_urls no match for title=%s", raw_title
        #             )
        #             continue

        #         hit = hits[0]
        #         doc_id = str(hit.get("_id", "")).strip()
        #         source = hit.get("_source", {}) or {}
        #         title = source.get("title") or doc_id or raw_title
        #         title_str = _clean_text(str(title))
        #         source_from = source.get("from")

        #         url = None

        #         if isinstance(source_from, str):
        #             template = url_suffix_map.get(source_from)
        #             if template:
        #                 url = f"{base}{template.format(id=doc_id)}"

        #         if not url:
        #             for fallback_key in ("url", "sourceUrl", "link"):
        #                 candidate = source.get(fallback_key)
        #                 if isinstance(candidate, str) and candidate.strip():
        #                     url = candidate.strip()
        #                     break

        #         if not url:
        #             url = f"{base}document/{doc_id}"

        #         markdown_links.append(f"- [{title_str}]({url})")

        #     final_output = "\n".join(markdown_links)

        #     self.logger.info(
        #         "build_chinataxcenter_urls generated %s links", len(markdown_links)
        #     )

        #     return final_output



        # @mcp.tool()
        # def list_chinataxcenter_tax_type(
        #     index: str = "chinataxcenter_new",
        #     size: int = 1000,
        #     effectiveness: Optional[str] = "有效",
        #     min_count: int = 1,
        # ) -> str:
        #     """List each taxType with its document count.

        #     Args:
        #         index: Target index name (default: 'chinataxcenter_new')
        #         size: Maximum unique terms to return for taxType

        #     Curl example (Top-K taxType distribution):
        #         curl -u "$ELASTICSEARCH_USERNAME:$ELASTICSEARCH_PASSWORD" -H 'Content-Type: application/json' -X POST \
        #         "http://localhost:9200/chinataxcenter_new/_search" -d '{
        #           "size": 0,
        #           "query": {
        #             "bool": { "filter": [ { "match": { "effectiveness": "有效" } } ] }
        #           },
        #           "aggs": {
        #             "taxType": {
        #               "terms": { "field": "taxType.keyword", "size": 1000, "min_doc_count": 1 }
        #             }
        #           }
        #         }'

        #     Curl example (Top-K with runtime_mappings, no index mapping change):
        #         curl -u "$ELASTICSEARCH_USERNAME:$ELASTICSEARCH_PASSWORD" -H 'Content-Type: application/json' -X POST \
        #         "http://localhost:9200/chinataxcenter_new/_search" -d '{
        #           "size": 0,
        #           "query": {
        #             "bool": { "filter": [ { "match": { "effectiveness": "有效" } } ] }
        #           },
        #           "runtime_mappings": {
        #             "taxType_kw": {
        #               "type": "keyword",
        #               "script": "emit(params._source.containsKey(\\"taxType\\") ? params._source.taxType : null)"
        #             }
        #           },
        #           "aggs": {
        #             "taxType": {
        #               "terms": { "field": "taxType_kw", "size": 1000, "min_doc_count": 1 }
        #             }
        #           }
        #         }'
        #     """
        #     aggs: Dict = {
        #         "taxType": {
        #             "terms": {
        #                 "field": "taxType.keyword",
        #                 "size": max(size, 1),
        #                 "min_doc_count": max(min_count, 0),
        #             }
        #         }
        #     }
        #     query_filters: List[Dict] = []
        #     if effectiveness:
        #         query_filters.append({"match": {"effectiveness": effectiveness}})
        #     query: Dict = {"bool": {"filter": query_filters}} if query_filters else {"match_all": {}}
        #     body: Dict = {"size": 0, "query": query, "aggs": aggs}

        #     result: Dict = self.search_client.search_documents(index=index, body=body)

        #     buckets: List[Dict] = result.get("aggregations", {}).get("taxType", {}).get("buckets", [])
        #     tax_type_counts = {
        #         b.get("key"): int(b.get("doc_count", 0))
        #         for b in buckets
        #         if b.get("key") not in (None, "") and int(b.get("doc_count", 0)) >= max(min_count, 0)
        #     }

        #     return str(tax_type_counts)



        # @mcp.tool()
        # def list_chinataxcenter_topics(
        #     index: str = "chinataxcenter_new",
        #     size: int = 1000,
        #     effectiveness: Optional[str] = "有效",
        #     min_count: int = 1,
        # ) -> str:
        #     """List each topic with its document count.

        #     Args:
        #         index: Target index name (default: 'chinataxcenter_new')
        #         size: Maximum unique terms to return for topic

        #     Curl example (Top-K topic distribution):
        #         curl -u "$ELASTICSEARCH_USERNAME:$ELASTICSEARCH_PASSWORD" -H 'Content-Type: application/json' -X POST \
        #         "http://localhost:9200/chinataxcenter_new/_search" -d '{
        #           "size": 0,
        #           "query": {
        #             "bool": { "filter": [ { "match": { "effectiveness": "有效" } } ] }
        #           },
        #           "aggs": {
        #             "topic": {
        #               "terms": {
        #                 "field": "topic.keyword",
        #                 "size": 1000,
        #                 "order": { "_count": "desc" },
        #                 "min_doc_count": 1
        #               }
        #             }
        #           }
        #         }'

        #     Curl example (Top-K with runtime_mappings, no index mapping change):
        #         curl -u "$ELASTICSEARCH_USERNAME:$ELASTICSEARCH_PASSWORD" -H 'Content-Type: application/json' -X POST \
        #         "http://localhost:9200/chinataxcenter_new/_search" -d '{
        #           "size": 0,
        #           "query": {
        #             "bool": { "filter": [ { "match": { "effectiveness": "有效" } } ] }
        #           },
        #           "runtime_mappings": {
        #             "topic_kw": {
        #               "type": "keyword",
        #               "script": "emit(params._source.containsKey(\\"topic\\") ? params._source.topic : null)"
        #             }
        #           },
        #           "aggs": {
        #             "topic": {
        #               "terms": {
        #                 "field": "topic_kw",
        #                 "size": 1000,
        #                 "order": { "_count": "desc" },
        #                 "min_doc_count": 1
        #               }
        #             }
        #           }
        #         }'
        #     """
        #     aggs: Dict = {
        #         "topic": {
        #             "terms": {
        #                 "field": "topic.keyword",
        #                 "size": max(size, 1),
        #                 "order": {"_count": "desc"},
        #                 "min_doc_count": max(min_count, 0),
        #             }
        #         }
        #     }
        #     query_filters: List[Dict] = []
        #     if effectiveness:
        #         query_filters.append({"match": {"effectiveness": effectiveness}})
        #     query: Dict = {"bool": {"filter": query_filters}} if query_filters else {"match_all": {}}
        #     body: Dict = {"size": 0, "query": query, "aggs": aggs}

        #     result: Dict = self.search_client.search_documents(index=index, body=body)

        #     buckets: List[Dict] = result.get("aggregations", {}).get("topic", {}).get("buckets", [])
        #     topic_counts: Dict[str, int] = {
        #         b.get("key"): int(b.get("doc_count", 0))
        #         for b in buckets
        #         if b.get("key") not in (None, "") and int(b.get("doc_count", 0)) >= max(min_count, 0)
        #     }

        #     return str(topic_counts)



def _clean_text(text: str) -> str:
    try:
        if not isinstance(text, str):
            return text
        cleaned = text
        # Remove one-or-more backslashes before escape letters (handles \\r, \\\n, etc.)
        cleaned = re.sub(r"\\+r", " ", cleaned)
        cleaned = re.sub(r"\\+n", " ", cleaned)
        cleaned = re.sub(r"\\+t", " ", cleaned)
        cleaned = re.sub(r"\\+u3000", " ", cleaned, flags=re.IGNORECASE)
        # Remove actual control characters and ideographic space
        cleaned = (
            cleaned.replace("\r", " ")
                    .replace("\n", " ")
                    .replace("\t", " ")
                    .replace("\u3000", " ")
        )
        # Collapse multiple spaces
        cleaned = " ".join(cleaned.split())
        return cleaned
    except Exception:
        return text