from typing import Any, Dict, List
from app.schemas.chat_query_schema import ChatQueryResponse, ExecutionStatus, PendingQuestion


class ResponseAggregatorService:
    """Combines multi-branch workflow results into a cohesive civic intelligence response.

    Preserves citations, source distinctions (live NeGD vs. verified demo dataset),
    document page numbers, and transparent partial failure reporting.
    """

    @classmethod
    def aggregate(cls, state: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate domain outputs and produce natural language summary and structured payload."""
        intent = state.get("intent", "GENERAL_QUERY")
        lang = state.get("language", "en")
        task_status = state.get("task_status", {})
        errors = state.get("errors", [])
        user_query = state.get("user_query", "")

        law_results = state.get("law_results", [])
        scheme_results = state.get("scheme_results", [])
        doc_results = state.get("document_results", [])
        eligibility = state.get("eligibility_results", {})
        pending_questions_raw = state.get("pending_questions", [])

        completed_tasks = [k for k, v in task_status.items() if v == "COMPLETED"]
        failed_tasks = [k for k, v in task_status.items() if v == "FAILED"]
        has_partial_failure = len(completed_tasks) > 0 and len(failed_tasks) > 0

        sources: List[Dict[str, Any]] = []
        answer_parts: List[str] = []

        # 1. GREETING / GENERAL / UNSUPPORTED HANDLERS
        if intent == "GENERAL_QUERY":
            if lang == "te":
                answer = "నమస్కారం! నేను నీతిసేతు (NitiSetu) సివిక్ అసిస్టెంట్‌ని. మీకు ప్రభుత్వ పథకాలు, హక్కులు మరియు చట్టాలు అర్థం చేసుకోవడంలో సహాయం చేయగలను. మీరు ఏమి తెలుసుకోవాలనుకుంటున్నారు?"
            elif lang == "hi":
                answer = "नमस्ते! मैं नीतिसेतु (NitiSetu) नागरिक सूचना सहायक हूँ। मैं आपको सरकारी योजनाओं, अधिकारों और कानूनों को सरल भाषा में समझने में सहायता कर सकता हूँ। आप क्या जानना चाहते हैं?"
            else:
                answer = "Namaste! I am NitiSetu, your civic information assistant. I can explain government welfare schemes, help you evaluate eligibility conditions, search Indian statutory laws and citizen rights, and analyze uploaded government gazettes and orders. How can I help you today?"

            return {
                "final_response": answer,
                "response_metadata": {
                    "sources": [],
                    "citations": [],
                    "completed_tasks": completed_tasks,
                    "failed_tasks": failed_tasks,
                    "partial_failure": False,
                },
            }

        if intent == "UNSUPPORTED_QUERY":
            if lang == "te":
                answer = "క్షమించండి, మీ ప్రశ్న ప్రస్తుతం నీతిసేతు పరిధిలోకి రాదు. నేను భారతీయ చట్టాలు, పౌర హక్కులు, ప్రభుత్వ సంక్షేమ పథకాలు మరియు అధికారిక నోటీసుల గురించి మాత్రమే సహాయం అందించగలను."
            elif lang == "hi":
                answer = "क्षमा करें, आपका प्रश्न वर्तमान में नीतिसेतु के दायरे में नहीं है। मैं केवल भारतीय कानूनों, नागरिक अधिकारों, सरकारी योजनाओं और आधिकारिक सरकारी आदेशों पर सहायता प्रदान कर सकता हूँ।"
            else:
                answer = "I apologize, but this query falls outside NitiSetu's civic scope. I am specifically built to explain Indian laws and citizen rights, government welfare schemes and eligibility, and uploaded official circulars or gazettes."

            return {
                "final_response": answer,
                "response_metadata": {
                    "sources": [],
                    "citations": [],
                    "completed_tasks": completed_tasks,
                    "failed_tasks": failed_tasks,
                    "partial_failure": False,
                },
            }

        # 2. DOCUMENT INTELLIGENCE COMPONENT
        if doc_results:
            for doc in doc_results:
                fname = doc.get("original_filename", "Uploaded Document")
                total_p = doc.get("total_pages", len(doc.get("pages", [])))
                status = doc.get("processing_status", "COMPLETED")

                if status == "OCR_REQUIRED":
                    answer_parts.append(
                        f"📄 **Uploaded Document ({fname}):**\n"
                        f"This document contains {total_p} page(s) but has negligible extractable digital text. "
                        "It appears to be a scanned notice or image-based circular requiring OCR."
                    )
                else:
                    pages = doc.get("pages", [])
                    preview_texts = []
                    for p in pages[:2]:
                        p_num = p.get("page_number", 1)
                        snippet = p.get("text", "")[:350]
                        if snippet:
                            preview_texts.append(f"- *Page {p_num}:* {snippet}...")
                    
                    preview_joined = "\n".join(preview_texts) if preview_texts else "Digital text extracted successfully."
                    answer_parts.append(
                        f"📄 **Uploaded Document Analysis ({fname} - {total_p} Page(s)):**\n{preview_joined}"
                    )

                sources.append({
                    "title": f"Document: {fname}",
                    "source": "Uploaded Citizen Document",
                    "type": "uploaded_user_pdf",
                    "url": f"document://{doc.get('document_id')}",
                    "details": f"{total_p} page(s) processed with PyMuPDF",
                })

        # 3. SCHEME DETAILS COMPONENT
        if scheme_results:
            for s in scheme_results:
                s_name = s.get("scheme_name", "Welfare Scheme")
                ministry = s.get("ministry", "Government of India")
                desc = s.get("short_description", "")
                benefits = s.get("benefits", [])
                eligibility_rules = s.get("eligibility_conditions", [])
                source_url = s.get("official_source_url", "https://myscheme.gov.in")

                benefits_list = "\n".join([f"  • {b}" for b in benefits[:3]]) if benefits else "Financial support."
                answer_parts.append(
                    f"🌾 **Government Scheme: {s_name}**\n"
                    f"*Implementing Authority:* {ministry}\n"
                    f"{desc}\n\n"
                    f"**Key Entitlements:**\n{benefits_list}"
                )

                sources.append({
                    "title": s_name,
                    "source": "Official Government Portal (Verified Demo Dataset)",
                    "type": "verified_demo_dataset",
                    "url": source_url,
                    "details": f"Verified official rules ({s.get('last_verified', '2025-01-15')})",
                })

        # 4. ELIGIBILITY EVALUATION COMPONENT
        if eligibility:
            overall = eligibility.get("overall_result", "NEEDS_MORE_INFORMATION")
            scheme_title = eligibility.get("scheme_name", "Welfare Scheme")
            conds = eligibility.get("conditions", [])
            disclaimer = eligibility.get("disclaimer", "Preliminary assessment.")

            cond_summaries = []
            for c in conds:
                st = c.get("status", "UNKNOWN")
                icon = "✅" if st == "MET" else "❌" if st == "NOT_MET" else "❓"
                cond_summaries.append(f"  {icon} {c.get('condition')}: {c.get('explanation')}")

            cond_text = "\n".join(cond_summaries)

            if overall == "LIKELY_ELIGIBLE":
                status_heading = "🎉 **Eligibility Assessment: LIKELY ELIGIBLE**"
            elif overall == "LIKELY_NOT_ELIGIBLE":
                status_heading = "⚠️ **Eligibility Assessment: LIKELY INELIGIBLE**"
            else:
                status_heading = "ℹ️ **Eligibility Assessment: NEEDS MORE INFORMATION**"

            answer_parts.append(
                f"{status_heading} for *{scheme_title}*\n\n"
                f"**Condition Breakdown:**\n{cond_text}\n\n"
                f"*Note:* {disclaimer}"
            )

        # 5. LAW STATUTES COMPONENT (NYAYKOSH)
        if law_results:
            law_summaries = []
            for item in law_results[:3]:
                sec = item.get("section_number", "Section")
                law = item.get("law_name", "Indian Statute")
                txt = item.get("content", "")
                url = item.get("source_url", "https://lawascode.negd.in")
                law_summaries.append(f"⚖️ **{law} ({sec}):**\n\"{txt}\"")

                sources.append({
                    "title": f"{law} - {sec}",
                    "source": "NeGD NyayKosh Official Legal Repository",
                    "type": "nyaykosh_legal_retrieval",
                    "url": url,
                    "details": "NeGD Law as Code statutory repository",
                })

            answer_parts.append("\n\n".join(law_summaries))

        # 6. REPORT PARTIAL FAILURES IF ANY
        if has_partial_failure:
            failed_str = ", ".join(failed_tasks)
            answer_parts.append(
                f"\n⚠️ *Partial Service Notice:* Retrieval for [{failed_str}] encountered a temporary upstream issue. "
                "The available results have been compiled above without interruption."
            )

        # If no domain branches returned data and there were errors
        if not answer_parts:
            if errors:
                err_msgs = "; ".join([e.get("error", "Error") for e in errors])
                final_answer = (
                    f"I encountered difficulty retrieving information for your query: {err_msgs}. "
                    "Please verify your query or try searching by specific scheme or law name."
                )
            else:
                final_answer = (
                    "I could not locate matching records for your query. "
                    "You can explore our verified welfare schemes, search for specific laws like the Consumer Protection Act, "
                    "or upload an official government circular PDF."
                )
        else:
            final_answer = "\n\n---\n\n".join(answer_parts)

        return {
            "final_response": final_answer,
            "response_metadata": {
                "sources": sources,
                "citations": sources,
                "completed_tasks": completed_tasks,
                "failed_tasks": failed_tasks,
                "partial_failure": has_partial_failure,
            },
        }
