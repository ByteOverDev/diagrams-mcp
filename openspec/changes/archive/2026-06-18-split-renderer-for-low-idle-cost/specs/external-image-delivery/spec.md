## ADDED Requirements

### Requirement: Rendered outputs can be stored outside process memory
The system SHALL support storing rendered image outputs in an external temporary storage backend rather than requiring process-local memory retention for download URLs.

#### Scenario: Download link requested
- **WHEN** a render tool returns a download link
- **THEN** the rendered bytes are retrievable from external storage without relying on the facade process memory store

#### Scenario: Large output rendered
- **WHEN** a rendered output is too large for inline return but within the configured delivery limit
- **THEN** the system stores the output externally and returns a temporary download URL

### Requirement: Temporary output URLs remain unguessable and time-bounded
The system SHALL use unguessable output identifiers and SHALL enforce a configured expiration policy for temporary rendered outputs.

#### Scenario: Valid temporary URL
- **WHEN** a client fetches a temporary output URL before expiration
- **THEN** the system returns the rendered artifact with the correct content type

#### Scenario: Expired temporary URL
- **WHEN** a client fetches a temporary output URL after expiration
- **THEN** the system returns a not found or expired response

### Requirement: External delivery preserves output format behavior
The system SHALL preserve existing output format semantics for PNG, SVG, and PDF where the underlying renderer supports them.

#### Scenario: SVG output requested
- **WHEN** a client requests an SVG output that is not suitable for inline image return
- **THEN** the system returns a download link for the SVG artifact

#### Scenario: PDF output requested
- **WHEN** a client requests a PDF output from a renderer that supports PDF
- **THEN** the system returns a download link for the PDF artifact
