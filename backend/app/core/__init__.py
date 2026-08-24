"""Business logic layer package.

Contains the analysis orchestration, prompt building, and context retrieval
logic. This layer depends only on the abstractions defined in ``repository``
and ``llm`` — never on their concrete implementations (see Requirements
12.2, 12.3).
"""
