---
name: vpn-evidence-workbench
description: Design and implement the VPN platform knowledge question-answering module with user questions, follow-ups, grounded explanations and inspectable sources.
---

# VPN evidence workbench

Keep the existing Vue, Element Plus, dark navigation, green actions and restrained cyan technical accents.
Use IBM Plex Sans for Latin text and existing Chinese fallback fonts. Preserve existing visual tokens.

The module is a domain Q&A assistant. The user's question and explanatory answer are the primary interaction.
Support concept questions, why/how questions and follow-ups. Use a conversation area with a source inspector
alongside it; collapse to one column on mobile. Do not replace Q&A with an evidence collection workflow.

Keep retrieved knowledge separate from flow facts. Show source, section, version and stable chunk ID in the
inspector. Put hashes and raw JSON behind details. Label relevance scores as ranking scores, never risk scores.
Clicking a citation should show its matching original source. References do not prove semantic correctness.

Make empty results, loading, retrieval errors and source failures explicit. Preserve conversation history when
asking follow-ups. Offer a new-conversation action. Label extractive offline results separately from LLM answers.
Verify questions, follow-ups, citations, reset, failure states and mobile overflow in a real browser.

For knowledge answers, use the runtime vpn-knowledge-qa skill shipped with the backend. Keep API keys
server-side. Display which provider ran and distinguish model prose from structurally validated references.
