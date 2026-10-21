import {apiRequest,ApiClientError} from "./client";
import {API_BASE_URL} from "../constants";

export type ReviewDecision="CONFIRM"|"UNCERTAIN"|"REJECT";
export type MotifReviewReasonCode=
 "VISUAL_MATCH_CONFIRMED"|"INSUFFICIENT_VISUAL_EVIDENCE"|"AMBIGUOUS_WITH_OTHER_MOTIF"|
 "REGION_INCORRECT"|"ONTOLOGY_MAPPING_INCORRECT"|"NOT_A_MOTIF"|"CROP_OR_OCCLUSION_LIMITATION"|"OTHER";
export interface MotifReviewQueueItem {
 review_subject_id:string;analysis_id:string;candidate_id:string;visual_candidate_key:string;
 proposed_canonical_motif_key:string|null;original_candidate_status:string;candidate_confidence:number;
 created_at:string;effective_status:string;review_version:number;research_eligibility:string;image_url?:string|null;
}
export interface MotifReviewDetail extends MotifReviewQueueItem {
 candidate_region:Record<string,unknown>;visual_evidence:string[];model_provenance:Record<string,unknown>;
 snapshot_hash:string;ontology_version:string;history_count:number;image_available:boolean;
}
export interface MotifReviewEvent {
 review_id:string;review_subject_id:string;decision:ReviewDecision;resulting_status:string;
 selected_canonical_motif_key:string|null;reason_code:MotifReviewReasonCode|null;note:string|null;
 reviewer_ref:string;reviewer_boundary:string;candidate_snapshot_hash:string;idempotency_key:string;
 version:number;created_at:string;supersedes_review_id?:string|null;
}
interface QueueResponse {items:MotifReviewQueueItem[];total_count:number;limit:number;offset:number;status_filter:string|null}
export class ReviewApiError extends Error{
 constructor(public readonly code:string,message:string,public readonly status:number=0){super(message);this.name="ReviewApiError";}
}
const root="/api/v1/reviews/motif-candidates";
async function request<T>(path:string,options?:RequestInit):Promise<T>{
 try{return await apiRequest<T>(path,options)}
 catch(e){if(e instanceof ApiClientError) throw new ReviewApiError(e.code,e.message,e.status);throw e}
}
function absoluteImage<T extends {image_url?:string|null}>(item:T):T{
 if(item.image_url?.startsWith("/"))return {...item,image_url:API_BASE_URL+item.image_url};
 return item;
}
export async function fetchMotifReviewQueue(status:string="PENDING",limit=50,offset=0):Promise<QueueResponse>{
 const params=new URLSearchParams({status,limit:String(limit),offset:String(offset)});
 const res=await request<QueueResponse>(`${root}?${params.toString()}`);
 return {...res,items:res.items.map(absoluteImage)};
}
export async function fetchMotifReviewDetail(id:string):Promise<MotifReviewDetail>{
 return absoluteImage(await request<MotifReviewDetail>(`${root}/${encodeURIComponent(id)}`));
}
export function fetchMotifReviewHistory(id:string):Promise<MotifReviewEvent[]>{
 return request<MotifReviewEvent[]>(`${root}/${encodeURIComponent(id)}/history`);
}
export async function submitMotifReviewDecision(
 id:string,body:{decision:ReviewDecision;selected_canonical_motif_key?:string|null;
 reason_code?:MotifReviewReasonCode|null;note?:string|null;expected_version:number},
 idempotencyKey:string
){
 return request(`${root}/${encodeURIComponent(id)}/decision`,{
 method:"POST",headers:{"Idempotency-Key":idempotencyKey},body:JSON.stringify(body)
 });
}
