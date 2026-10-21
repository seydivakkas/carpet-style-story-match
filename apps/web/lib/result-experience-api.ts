import {apiRequest} from "./api/client";
import {API_BASE_URL} from "./constants";
export type SectionState="READY"|"NOT_AVAILABLE"|"WAITING_FOR_REVIEW"|"WAITING_FOR_RESEARCH"|"BLOCKED_BY_QUALITY";
interface ColorItem{label:string;hex_code?:string|null;coverage_percentage:number;turkish_description:string}
interface CatalogMatch{rank:number;catalog_id:string;sku:string;brand?:string|null;collection?:string|null;product_name:string;primary_image_url?:string|null;visual_proximity_score:number;closest_dimensions:string[]}
export interface VisualCharacterCardData{
 state:SectionState;style_dna_version:string;dimensions:Record<string,number>;palette:ColorItem[];
 composition:Record<string,unknown>;catalog_matches:CatalogMatch[];
}
interface MotifCandidate{candidate_id:string;visual_descriptor:string;turkish_label:string;ai_confidence:number;bounding_box?:number[]|null;status:string;confirmed_canonical_motif_key?:string|null}
export interface MotifCardData{state:SectionState;candidates:MotifCandidate[];review_summary:{total_candidates:number;confirmed_count:number;pending_count:number;uncertain_count:number;rejected_count:number}}
interface ClaimSource{institution:string;title:string;locator:string;excerpt?:string|null;canonical_url?:string|null}
export interface CulturalClaimItem{claim_id:string;status:string;statement_tr:string;scope?:string|null;sources:ClaimSource[]}
export interface CulturalContextCardData{state:SectionState;user_message?:string|null;claims:CulturalClaimItem[]}
interface StorySection{heading:string;content:string;citations:string[];is_contested:boolean}
export interface MotifStoryCardData{state:SectionState;user_message?:string|null;story?:{title:string;summary:string;sections:StorySection[]}|null;thematic_affinity?:{matched_themes:string[];affinity_description:string}|null}
interface HistoricalMatch{rank:number;historical_reference_id:string;reference_key:string;institution:string;object_title:string;museum_object_id?:string|null;canonical_source_url?:string|null;primary_image_url?:string|null;date_or_period?:string|null;origin_culture?:string|null;origin_geography?:string|null;medium_materials?:string|null;visual_proximity_score:number;closest_dimensions:string[]}
export interface HistoricalConnectionsCardData{state:SectionState;disclaimer:string;matches:HistoricalMatch[]}
export interface UnifiedUploadResult{
 schema_version:string;analysis_id:string;
 image_meta:{original_sha256:string;prepared_sha256?:string|null;original_width?:number|null;original_height?:number|null;primary_image_url:string};
 visual_character:VisualCharacterCardData;motifs:MotifCardData;cultural_context:CulturalContextCardData;
 motif_story:MotifStoryCardData;historical_connections:HistoricalConnectionsCardData;
 provenance:{analysis_contract_version:string;style_dna_version:string;color_version:string;vlm_provider_version?:string|null;review_version?:string|null;
 visual_retrieval_version:string;catalog_corpus_fingerprint?:string|null;historical_corpus_fingerprint?:string|null};
 warnings:string[];
}
export interface AcceptedAnalysis{analysis_id:string;status:string;poll_url:string;access_token:string}
export interface AnalysisStatus{analysis_id:string;status:"PROCESSING"|"COMPLETED"|"FAILED"|"BLOCKED_BY_QUALITY";error?:string|null}
/** Sunucudaki analiz kimliğine özel bearer kanıtı, asla URL'de taşınmaz. */
const tokenKey=(id:string)=>`carpet_analysis_secret_${id}`;
function analysisHeaders(id:string):HeadersInit{
 const token=typeof window==="undefined"?null:window.localStorage.getItem(tokenKey(id));
 return token?{"X-Analysis-Token":token}:{};
}
export async function startAnalysis(file:File):Promise<AcceptedAnalysis>{
 const body=new FormData();body.append("file",file);
 const res=await apiRequest<AcceptedAnalysis>("/api/v1/upload-analysis/unified-result",{method:"POST",body});
 if(!res.access_token)throw new Error("Sunucu analiz erişim anahtarı üretmedi.");
 try{
   window.localStorage.setItem(tokenKey(res.analysis_id),res.access_token);
 }catch{
   throw new Error("Analiz oluşturuldu ancak erişim anahtarı kaydedilemedi. Tarayıcı depolama izinlerini kontrol edin.");
 }
 return res;
}
export function fetchAnalysisStatus(id:string){
 return apiRequest<AnalysisStatus>(`/api/v1/upload-analysis/${encodeURIComponent(id)}/status`,{headers:analysisHeaders(id)});
}
export async function fetchUnifiedResultById(id:string):Promise<UnifiedUploadResult>{
 const res=await apiRequest<UnifiedUploadResult>(`/api/v1/upload-analysis/${encodeURIComponent(id)}/unified-result`,{headers:analysisHeaders(id)});
 const path=res.image_meta.primary_image_url;
 return {...res,image_meta:{...res.image_meta,primary_image_url:path.startsWith("/")?API_BASE_URL+path:path}};
}
/** Görsel isteği özel başlıkla yapılır; erişim anahtarı URL/log/referrer'a girmez. */
export async function fetchAnalysisImageObjectUrl(id:string):Promise<string>{
 const response=await fetch(`${API_BASE_URL}/api/v1/upload-analysis/${encodeURIComponent(id)}/image`,{
   headers:analysisHeaders(id),cache:"no-store"
 });
 if(!response.ok)throw new Error(`Görsel erişimi başarısız: HTTP ${response.status}`);
 const blob=await response.blob();
 if(!blob.type.startsWith("image/"))throw new Error("Sunucudan beklenmeyen görsel içeriği.");
 return URL.createObjectURL(blob);
}
export async function deleteAnalysisRecord(id:string){
 const result=await apiRequest<{status:string;analysis_id:string}>(`/api/v1/upload-analysis/${encodeURIComponent(id)}`,{
   method:"DELETE",headers:analysisHeaders(id)
 });
 if(typeof window!=="undefined")window.localStorage.removeItem(tokenKey(id));
 return result;
}

/** Bilimsel model kalitesi, dosya varlığından bağımsız HOLD olarak raporlanır. */
export interface ModelAcceptance {
 status:"HOLD"; model_quality:"NOT_VALIDATED";approved_for_production:boolean;
 independent_holdout_verified:boolean;missing_artifacts:string[];
 checked_artifacts:number;available_artifacts:number;caution_tr:string;
}
export function fetchModelAcceptance():Promise<ModelAcceptance>{
 return apiRequest<ModelAcceptance>("/api/v1/system/model-acceptance");
}
