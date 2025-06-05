# FastSlug - An Extensible AI Agent System
FastSlug is an extensible AI agent platform that intelligently selects and coordinates specialized AI agents to handle users' requests.

```mermaid
flowchart TD
    UserRequest["User Request"]
    Secretary["Secretary Agent"]
    Candidates["Agent Candidates"]
    Selected["Selected Agents"]
    Result["Result"]

    UserRequest --> Secretary
    Secretary -- Selection --> Candidates
    Secretary -- Delegation --> Selected
    Selected --> Result
    Result -.->|User Feedback| Secretary
```

*Figure: Overview of the FastSlug agent selection and coordination process.*