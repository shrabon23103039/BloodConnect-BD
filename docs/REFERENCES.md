# References and Engineering Guidance

This document lists primary references used to establish the proposed technical baseline. Re-check official documentation before implementation and whenever dependencies are upgraded.

## Framework and deployment references

1. Django 5.2 release notes and LTS information:  
   https://docs.djangoproject.com/en/5.2/releases/5.2/

2. Django 5.2 release series and supported Python versions:  
   https://docs.djangoproject.com/en/5.2/releases/5.2/

3. Python 3.14.10 release and security fixes:
   https://www.python.org/downloads/release/python-31410/

4. Django deployment checklist:
   https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

5. Django REST Framework release notes:
   https://www.django-rest-framework.org/community/release-notes/

6. Cursor rules documentation:
   https://docs.cursor.com/context/rules-for-ai

7. Anthropic Claude Code documentation:
   https://docs.anthropic.com/en/docs/claude-code/overview

8. Anthropic Claude Code memory / project instructions documentation (check current navigation):
   https://docs.anthropic.com/en/docs/claude-code/memory

9. Bootstrap 5.3.8 compiled assets, integrity and license information:
   https://getbootstrap.com/docs/5.3/getting-started/download/

## Context engineering and specification-driven development

The package uses a practical four-layer context structure:
1. Product/domain context — PRD, app flows and data governance.
2. Architecture/technical context — TRD, schema, API and ADRs.
3. Execution context — implementation plan and agent instructions.
4. Validation/operations context — testing, security, deployment and release criteria.

This is the project's adopted organization model, not a claim that one universally standardized or official "Four-Layer Context Engineering Framework" exists.

The user-provided phrase "Spec-Driven Development with Claude Code" is treated as a workflow concept: requirements and design are written first, implementation tasks are derived from specifications, and completion is checked against acceptance criteria. Consult current Anthropic guidance and the selected agent's documentation before adopting tool-specific commands.

## Bangladesh-specific review sources

- DGHS Bangladesh Core FHIR Implementation Guide: https://fhir.dghs.gov.bd/core/
- Bangladesh FHIR sandbox: https://sandbox.fhir.dghs.gov.bd/fhir

These resources do not imply that BloodConnect BD has authorization to access production health systems. Any production integration requires formal approval, API documentation, credentials, data-sharing basis and security review.

## Version notes

At preparation time, Django 5.2 is an LTS series and DRF 3.18.3 is listed in official DRF release notes. Proposed exact pins are recorded in `04_TRD.md`; verify package availability, support matrix and security advisories before locking the environment.
