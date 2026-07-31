# Delta for user-preference-memory

## ADDED Requirements

### Requirement: PreferenceStorage

The system MUST store user preferences as LongTermMemory entries with memory_type="preference".

#### Scenario: Create a new preference

- GIVEN a user ID and preference content (e.g., "response style: concise")
- WHEN CreatePreference is called
- THEN the system creates a LongTermMemory with memory_type="preference"
- AND the memory is linked to the user_id
- AND the memory status is ACTIVE

#### Scenario: Preference includes metadata

- GIVEN a preference with optional metadata (domain, confidence, source)
- WHEN CreatePreference is called
- THEN the metadata is stored in the memory's metadata field

### Requirement: PreferenceRetrieval

The system MUST retrieve user preferences by user ID and optional filters.

#### Scenario: Get all preferences for a user

- GIVEN a user ID with multiple preferences
- WHEN GetPreferencesByUser is called
- THEN the system returns all active preferences for that user

#### Scenario: Get preferences by tag

- GIVEN a user ID and tag (e.g., "response_style")
- WHEN GetPreferencesByUser with tag filter is called
- THEN the system returns preferences matching that tag

#### Scenario: Get preferences by category

- GIVEN a user ID and category (e.g., "communication")
- WHEN GetPreferencesByUser with category filter is called
- THEN the system returns preferences in that category

### Requirement: PreferenceUpdate

The system MUST update existing preferences.

#### Scenario: Update preference content

- GIVEN an existing preference ID and new content
- WHEN UpdatePreference is called
- THEN the system updates the content and updated_at timestamp
- AND the preference remains linked to the same user

#### Scenario: Update preference metadata

- GIVEN an existing preference ID and new metadata
- WHEN UpdatePreferenceMetadata is called
- THEN the system merges new metadata with existing metadata

### Requirement: PreferenceDeletion

The system MUST soft-delete preferences.

#### Scenario: Soft delete a preference

- GIVEN an existing preference ID
- WHEN DeletePreference is called
- THEN the system sets status=DELETED
- AND the preference is no longer returned in queries

#### Scenario: Permanent delete a preference

- GIVEN an existing preference ID
- WHEN PermanentDeletePreference is called
- THEN the system removes the preference from storage

### Requirement: PreferenceSearch

The system MUST search preferences by semantic similarity.

#### Scenario: Search preferences by query

- GIVEN a user ID and search query (e.g., "verbosity")
- WHEN SearchPreferences is called
- THEN the system returns preferences ranked by relevance to the query

#### Scenario: Search with limit

- GIVEN a user ID and limit parameter
- WHEN SearchPreferences is called with limit=5
- THEN the system returns at most 5 most relevant preferences

### Requirement: PreferenceConflictResolution

The system MUST handle conflicting preferences.

#### Scenario: Detect duplicate preferences

- GIVEN a user ID and a new preference that conflicts with existing
- WHEN CreatePreference is called
- THEN the system detects conflict via semantic similarity
- AND returns conflict details (existing preference ID, similarity score)

#### Scenario: Resolve conflict by superseding

- GIVEN a conflict detection result
- WHEN ResolvePreferenceConflict is called with resolution="supersede"
- THEN the existing preference status becomes CONSOLIDATED
- AND the new preference becomes ACTIVE