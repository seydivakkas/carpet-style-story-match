export type PreferenceAssessmentStatusEnum =
  | "CREATED"
  | "TEXT_PENDING"
  | "TEXT_COMPLETE"
  | "VISUAL_PENDING"
  | "VISUAL_COMPLETE"
  | "PROFILE_READY"
  | "PROFILE_REVIEWED"
  | "IMPORTANCE_COMPLETE"
  | "ABANDONED";

export type TextChoiceEnum =
  | "STRONGLY_A"
  | "SLIGHTLY_A"
  | "NEUTRAL"
  | "SLIGHTLY_B"
  | "STRONGLY_B";

export type VisualChoiceEnum =
  | "STRONGLY_LEFT"
  | "SLIGHTLY_LEFT"
  | "NEUTRAL"
  | "SLIGHTLY_RIGHT"
  | "STRONGLY_RIGHT";

export type ProvenanceEnum = "TEXT_ONLY" | "VISUAL_ONLY" | "MULTIMODAL" | "USER_OVERRIDE";

export type ImportanceLevelEnum = "MUST_HAVE" | "FLEXIBLE" | "STANDARD";

export type StyleDnaReadinessEnum =
  | "NO_PRIMARY_IMAGE"
  | "STYLE_DNA_MISSING"
  | "STYLE_DNA_FAILED"
  | "STYLE_DNA_PARTIAL"
  | "STYLE_DNA_COMPLETE";

export type StyleMatchStatusEnum = "COMPLETE" | "PARTIAL" | "NOT_AVAILABLE";
export type StyleMatchLabelEnum = "VERY_HIGH" | "HIGH" | "MODERATE" | "LOW";

export type NarrativeInterestLevelEnum = "PRIMARY" | "SECONDARY" | "NOT_SELECTED";

export type NarrativeAffinityStatusEnum = "COMPLETE" | "PARTIAL" | "NOT_AVAILABLE";
export type NarrativeAffinityLevelEnum = "VERY_STRONG" | "STRONG" | "MODERATE" | "LIMITED";

export type HistoricalConnectionStatusEnum = "COMPLETE" | "PARTIAL" | "NOT_AVAILABLE";
export type HistoricalConnectionLevelEnum = "VERY_CLOSE" | "CLOSE" | "MODERATE" | "LIMITED";

// --- API Error ---
export interface ApiErrorDetail {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

// --- Assessment ---
export interface PreferenceAssessmentRead {
  id: string;
  status: PreferenceAssessmentStatusEnum;
  current_step: string;
  created_at: string;
  updated_at: string;
}

// --- Text Questions Meta ---
export interface PreferenceTextQuestionRead {
  question_key: string;
  order: number;
  prompt_tr: string;
  option_a_tr: string;
  option_b_tr: string;
  primary_dimension: string;
  response_scale: string[];
}

export interface TextQuestionsListResponse {
  total_questions: number;
  questions: PreferenceTextQuestionRead[];
}

export interface TextResponseRead {
  question_key: string;
  choice: TextChoiceEnum;
}

// --- Visual Presentations ---
export interface VisualPresentationRead {
  id: string;
  stimulus_key: string;
  left_asset_url: string;
  right_asset_url: string;
}

export interface VisualResponseRead {
  stimulus_key: string;
  display_choice: VisualChoiceEnum;
}

// --- Preference Profile ---
export interface PreferenceDimensionRead {
  dimension_key: string;
  inferred_value: number;
  user_override_value?: number | null;
  final_value: number;
  provenance: ProvenanceEnum;
}

export interface UserPreferenceProfileResponse {
  id: string;
  assessment_id: string;
  profile_version: string;
  is_reviewed: boolean;
  is_confirmed: boolean;
  dimensions: PreferenceDimensionRead[];
  created_at: string;
  updated_at: string;
}

export interface DimensionConfidenceRead {
  dimension_key: string;
  confidence_score: number;
  confidence_level: "HIGH" | "MODERATE" | "LOW";
}

export interface PreferenceConfidenceProfileResponse {
  assessment_id: string;
  overall_confidence_score: number;
  overall_confidence_level: "HIGH" | "MODERATE" | "LOW";
  dimensions: DimensionConfidenceRead[];
}

export interface DimensionOverrideRequest {
  value: number;
}

// --- Importance Profile ---
export interface DimensionImportanceRead {
  dimension_key: string;
  importance_level: ImportanceLevelEnum;
  weight: number;
}

export interface ImportanceProfileResponse {
  id: string;
  assessment_id: string;
  is_skipped: boolean;
  dimensions: DimensionImportanceRead[];
  created_at: string;
}

export interface ImportanceSelectionRequest {
  skip: boolean;
  priority_dimensions: string[];
  flexible_dimensions: string[];
}

// --- User Narrative Profile ---
export type NarrativeCompletionModeEnum = "EXPLICIT_SELECTED" | "SKIPPED";

export interface UserNarrativeThemeRead {
  key: string;
  theme_key?: string;
  interest_level: NarrativeInterestLevelEnum;
  interest_weight: number;
  weight?: number;
}

export interface UserNarrativeProfileResponse {
  id: string;
  assessment_id: string;
  user_preference_profile_id?: string;
  profile_version: string;
  completion_mode: NarrativeCompletionModeEnum;
  is_skipped?: boolean;
  themes: UserNarrativeThemeRead[];
  selections?: UserNarrativeThemeRead[];
  created_at: string;
}

export interface NarrativeSelectionRequest {
  skip: boolean;
  primary_themes: string[];
  secondary_themes: string[];
}

// --- Manufacturer Brands ---
export interface BrandRead {
  id: string;
  brand_key: string;
  brand_name: string;
  brand_website?: string | null;
  logo_url?: string | null;
  is_verified: boolean;
  parser_module?: string | null;
  created_at: string;
  updated_at: string;
}

export interface BrandListResponse {
  total_count: number;
  brands: BrandRead[];
}

// --- Catalog Carpets ---
export interface PrimaryImageSummary {
  image_id: string;
  file_path: string;
  storage_key?: string;
  width: number;
  height: number;
  image_available?: boolean;
}

export interface CatalogCarpetRead {
  id: string;
  sku: string;
  name: string;
  description?: string | null;
  manufacturer?: string | null;
  collection?: string | null;
  width_cm?: number | null;
  height_cm?: number | null;
  material?: string | null;
  style_label?: string | null;
  source_type: string;
  source_reference?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  brand_id?: string | null;
  brand?: BrandRead | null;
}

export interface CatalogCarpetSummaryRead extends CatalogCarpetRead {
  primary_image?: PrimaryImageSummary | null;
  style_dna_readiness: StyleDnaReadinessEnum;
}

export interface StyleDimensionRead {
  key: string;
  value?: number | null;
  confidence: number;
  status: string;
  evidence?: Record<string, unknown>;
  method_version?: string;
}

export interface CarpetStyleProfileRead {
  id: string;
  carpet_id: string;
  image_id: string;
  algorithm_version: string;
  analysis_input_sha256: string;
  analysis_scope: string;
  status: string;
  analyzed_width_px: number;
  analyzed_height_px: number;
  created_at: string;
  dimensions: StyleDimensionRead[];
}

export interface CatalogCarpetDetailRead {
  carpet: CatalogCarpetRead;
  primary_image?: PrimaryImageSummary | null;
  style_dna_readiness: StyleDnaReadinessEnum;
  motif_association_count: number;
  story_association_count: number;
  motifs?: CarpetMotifAssociationRead[];
  style_profile_id?: string | null;
}

export interface CatalogCarpetListResponse {
  total_count: number;
  carpets: CatalogCarpetSummaryRead[];
}

export interface CarpetMotifAssociationRead {
  id: string;
  carpet_id: string;
  motif_id: string;
  motif_key: string;
  motif_name_tr: string;
  evidence_type: string;
  curation_note?: string | null;
  uncertainty_note?: string | null;
  story_association_count: number;
}

export interface CarpetStoryAssociationRead {
  id: string;
  carpet_motif_association_id: string;
  motif_key: string;
  motif_name_tr: string;
  motif_evidence_type: string;
  claim_id: string;
  claim_key: string;
  status: string;
  claim_text_tr?: string | null;
  context_note?: string | null;
  contest_note?: string | null;
  applicability_note?: string | null;
  themes: string[];
}

export interface ListCatalogCarpetsParams extends Record<string, unknown> {
  manufacturer?: string;
  brand_key?: string;
  collection?: string;
  material?: string;
  style_label?: string;
  readiness?: StyleDnaReadinessEnum;
  limit?: number;
  offset?: number;
}

// --- Visual Style Match ---
export interface StyleMatchDimensionResponse {
  dimension_key: string;
  user_value?: number | null;
  carpet_value?: number | null;
  importance_level: ImportanceLevelEnum;
  importance_weight: number;
  difference?: number | null;
  similarity?: number | null;
  weighted_similarity?: number | null;
  comparable: boolean;
}

export interface StyleMatchExplanationMatch {
  dimension_key: string;
  similarity: number;
  importance_level: ImportanceLevelEnum;
  importance_weight: number;
  user_value: number;
  carpet_value: number;
  narrative: string;
}

export interface StyleMatchExplanationDifference {
  dimension_key: string;
  difference: number;
  similarity: number;
  importance_level: ImportanceLevelEnum;
  importance_weight: number;
  impact: number;
  narrative: string;
}

export interface StyleMatchExplanationResponse {
  top_matches: StyleMatchExplanationMatch[];
  main_differences: StyleMatchExplanationDifference[];
  coverage_notes: string[];
  confidence_notes: string[];
}

export interface VisualStyleMatchResultResponse {
  id: string;
  assessment_id: string;
  user_preference_profile_id: string;
  importance_profile_id?: string | null;
  carpet_style_profile_id: string;
  match_version: string;
  status: StyleMatchStatusEnum;
  score?: number | null;
  score_100?: number | null;
  match_label?: StyleMatchLabelEnum | null;
  match_label_tr?: string | null;
  comparable_dimension_count: number;
  weighted_coverage: number;
  total_importance_weight: number;
  comparable_weight: number;
  dimensions: StyleMatchDimensionResponse[];
  explanation: StyleMatchExplanationResponse;
  created_at: string;
}

export interface StyleMatchCreateRequest {
  user_preference_profile_id: string;
  carpet_style_profile_id: string;
  importance_profile_id?: string | null;
}

// --- Narrative Affinity ---
export interface NarrativeAffinityThemeResultRead {
  theme_key: string;
  user_interest_level: NarrativeInterestLevelEnum;
  user_interest_weight: number;
  user_selected: boolean;
  carpet_support_status: string;
  confirmed_match: boolean;
  contested_overlap: boolean;
  has_contested_evidence?: boolean;
}

export interface AlignedThemeExplanationRead {
  theme_key: string;
  user_interest_level: NarrativeInterestLevelEnum;
  carpet_support_status: string;
  summary_tr: string;
}

export interface UnmatchedThemeExplanationRead {
  theme_key: string;
  user_interest_level: NarrativeInterestLevelEnum;
  carpet_support_status: string;
  summary_tr: string;
}

export interface ContestedOverlapExplanationRead {
  theme_key: string;
  user_interest_level: NarrativeInterestLevelEnum;
  contest_note?: string | null;
  summary_tr: string;
}

export interface NarrativeAffinityExplanationRead {
  overall_text_tr: string;
  aligned_themes: AlignedThemeExplanationRead[];
  unmatched_themes: UnmatchedThemeExplanationRead[];
  contested_overlaps: ContestedOverlapExplanationRead[];
}

export interface NarrativeAffinityResultRead {
  id: string;
  assessment_id: string;
  user_narrative_profile_id: string;
  carpet_id: string;
  affinity_version: string;
  status: NarrativeAffinityStatusEnum;
  affinity_level?: NarrativeAffinityLevelEnum | null;
  confirmed_interest_coverage?: number | null;
  selected_theme_count: number;
  confirmed_matched_theme_count: number;
  contested_overlap_count: number;
  created_at: string;
  theme_results: NarrativeAffinityThemeResultRead[];
}

export interface NarrativeAffinityDetailRead {
  result: NarrativeAffinityResultRead;
  explanation: NarrativeAffinityExplanationRead;
}

export interface NarrativeAffinityCreateRequest {
  carpet_id: string;
}

// --- Historical References ---
export interface HistoricalReferenceSummary {
  id: string;
  carpet_id: string;
  reference_key: string;
  institution_name: string;
  object_identifier: string;
  accession_number?: string | null;
  object_title: string;
  culture?: string | null;
  period?: string | null;
  dynasty_or_tradition?: string | null;
  date_display?: string | null;
  source_image_url?: string | null;
  created_at: string;
  style_dna_readiness?: StyleDnaReadinessEnum;
}

export interface HistoricalReferenceDetailRead {
  id: string;
  carpet_id: string;
  reference_key: string;
  institution_name: string;
  object_identifier: string;
  accession_number?: string | null;
  object_title: string;
  culture?: string | null;
  period?: string | null;
  dynasty_or_tradition?: string | null;
  date_display?: string | null;
  geography?: string | null;
  medium?: string | null;
  dimensions_text?: string | null;
  department?: string | null;
  credit_line?: string | null;
  object_url?: string | null;
  source_image_url?: string | null;
  curation_note?: string | null;
  primary_image?: PrimaryImageSummary | null;
  style_dna_readiness: StyleDnaReadinessEnum;
  created_at: string;
  updated_at: string;
}

export interface HistoricalReferenceListResponse {
  total_count: number;
  references: HistoricalReferenceSummary[];
}

export interface ListHistoricalReferencesParams extends Record<string, unknown> {
  museum?: string;
  institution?: string;
  region?: string;
  style_group?: string;
  readiness?: StyleDnaReadinessEnum;
  limit?: number;
  offset?: number;
}

// --- Historical Connections ---
export interface HistoricalConnectionDimensionRead {
  dimension_key: string;
  target_value?: number | null;
  target_status: string;
  target_confidence?: number | null;
  reference_value?: number | null;
  reference_status: string;
  reference_confidence?: number | null;
  difference?: number | null;
  similarity?: number | null;
  comparable: boolean;
}

export interface HistoricalConnectionExplanationRead {
  connection_level_label_tr?: string | null;
  closest_dimensions: Array<{
    dimension_key: string;
    similarity: number;
    target_value: number;
    reference_value: number;
  }>;
  main_differences: Array<{
    dimension_key: string;
    difference: number;
    target_value: number;
    reference_value: number;
  }>;
  disclaimer: string;
}

export interface HistoricalConnectionDetailRead {
  id: string;
  target_carpet_id: string;
  target_style_profile_id: string;
  historical_carpet_id: string;
  historical_reference_metadata_id: string;
  historical_style_profile_id: string;
  connection_version: string;
  status: HistoricalConnectionStatusEnum;
  style_similarity?: number | null;
  connection_level?: HistoricalConnectionLevelEnum | null;
  comparable_dimension_count: number;
  dimension_coverage: number;
  dimensions: HistoricalConnectionDimensionRead[];
  explanation: HistoricalConnectionExplanationRead;
  created_at: string;
}

export interface HistoricalConnectionSummaryRead {
  id: string;
  target_carpet_id: string;
  target_style_profile_id: string;
  historical_carpet_id: string;
  historical_reference_metadata_id: string;
  historical_style_profile_id: string;
  connection_version: string;
  status: HistoricalConnectionStatusEnum;
  style_similarity?: number | null;
  connection_level?: HistoricalConnectionLevelEnum | null;
  comparable_dimension_count: number;
  dimension_coverage: number;
  created_at: string;
}

export interface HistoricalConnectionListResponse {
  total_count: number;
  connections: HistoricalConnectionSummaryRead[];
}

export interface HistoricalConnectionCreateInput {
  target_style_profile_id: string;
  historical_reference_id: string;
}

export interface ListHistoricalConnectionsParams extends Record<string, unknown> {
  target_style_profile_id?: string;
  historical_reference_id?: string;
  connection_level?: HistoricalConnectionLevelEnum;
  limit?: number;
  offset?: number;
}

export interface HistoricalConnectionMetaResponse {
  connection_version: string;
  min_comparable_dimensions: number;
  statuses: string[];
  not_available_reasons: string[];
  connection_levels: string[];
}
