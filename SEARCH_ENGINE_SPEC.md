# Search Engine Specification

## Milestone 1: Index Construction

### Data Sources
1. **Information analyst**: small collection of web pages
2. **Algorithms and data structures developer**: larger collection of web pages

### Building the Inverted Index
The inverted index is a map with the **token** as key and a **list of postings** as value.

**Posting** (representation of token occurrence in a document) contains:
- Document name/id where the token was found
- Term frequency for that document (MS1: term frequency only; tf-idf in later milestones)

### Deliverables
- Code
- Report (PDF) with analytics table:
  - Number of indexed documents
  - Number of unique tokens
  - Total size (KB) of index on disk

### Evaluation Criteria
- Report submitted on time
- Plausible reported numbers
