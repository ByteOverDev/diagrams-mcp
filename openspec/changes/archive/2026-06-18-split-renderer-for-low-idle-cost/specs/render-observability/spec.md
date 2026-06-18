## ADDED Requirements

### Requirement: System reports idle and render memory metrics
The system SHALL provide enough runtime metrics or logs to distinguish facade idle memory from renderer memory during render execution.

#### Scenario: Facade idle measurement
- **WHEN** operators inspect the facade during an idle window
- **THEN** they can identify the facade memory baseline separately from renderer memory

#### Scenario: Renderer peak measurement
- **WHEN** a render operation completes
- **THEN** operators can inspect render-related metrics or logs that indicate render duration and resource usage at the renderer boundary

### Requirement: Render operations have structured lifecycle logs
The system SHALL emit structured logs for render request receipt, renderer dispatch, render completion, render failure, and output storage.

#### Scenario: Successful render
- **WHEN** a render operation succeeds
- **THEN** logs include the renderer type, requested format, duration, output delivery mode, and success status

#### Scenario: Failed render
- **WHEN** a render operation fails
- **THEN** logs include the renderer type, failure category, duration, and safe diagnostic details

### Requirement: Deployment comparison is possible
The system SHALL support comparing pre-split and post-split idle cost using Railway or equivalent platform metrics.

#### Scenario: Post-deployment review
- **WHEN** the split architecture is deployed
- **THEN** operators can compare current idle memory against the recorded pre-split baseline of approximately 0.69 GB
