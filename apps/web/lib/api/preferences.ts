import {useMutation,useQuery,useQueryClient} from "@tanstack/react-query";
import {apiRequest} from "./client";
import type {
 PreferenceAssessmentRead, PreferenceTextQuestionRead, TextResponseRead, TextChoiceEnum,
 VisualPresentationRead, VisualResponseRead, VisualChoiceEnum, UserPreferenceProfileResponse,
 PreferenceConfidenceProfileResponse, ImportanceProfileResponse, UserNarrativeProfileResponse,
 ImportanceSelectionRequest, NarrativeSelectionRequest
} from "../types/api";

const root="/api/v1/preference-assessments";
const key=(id:string)=>["assessment",id] as const;
const invalidate=(qc:ReturnType<typeof useQueryClient>,id:string)=>qc.invalidateQueries({queryKey:key(id)});
const post=<T,>(path:string)=>apiRequest<T>(path,{method:"POST"});
export function useCreateAssessment(){
 return useMutation({mutationFn:()=>post<PreferenceAssessmentRead>(root)});
}
export function useAssessment(id:string){
 return useQuery({queryKey:key(id),queryFn:()=>apiRequest<PreferenceAssessmentRead>(`${root}/${id}`),enabled:!!id});
}
export function useTextQuestionsMeta(){
 return useQuery({queryKey:["meta","text-questions"],queryFn:async()=>{
 const data=await apiRequest<{questions:PreferenceTextQuestionRead[]}>("/api/v1/meta/preference-text-questions");
 return data.questions;
 }});
}
export function useTextResponses(id:string){
 return useQuery({queryKey:[...key(id),"text-responses"],queryFn:()=>apiRequest<TextResponseRead[]>(`${root}/${id}/text-responses`),enabled:!!id});
}
export function useSaveTextResponse(id:string){
 const qc=useQueryClient();
 return useMutation({mutationFn:({questionKey,choice}:{questionKey:string;choice:TextChoiceEnum})=>
 apiRequest<TextResponseRead>(`${root}/${id}/text-responses/${encodeURIComponent(questionKey)}`,{method:"PUT",body:JSON.stringify({choice})}),
 onSuccess:()=>qc.invalidateQueries({queryKey:[...key(id),"text-responses"]})});
}
export function useCompleteTextAssessment(id:string){
 const qc=useQueryClient();
 return useMutation({mutationFn:()=>post<unknown>(`${root}/${id}/complete-text`),onSuccess:()=>invalidate(qc,id)});
}
export function useStartVisualPhase(id:string){
 const qc=useQueryClient();
 return useMutation({mutationFn:()=>post<VisualPresentationRead[]>(`${root}/${id}/start-visual`),
 onSuccess:()=>{invalidate(qc,id);qc.invalidateQueries({queryKey:[...key(id),"presentations"]});}});
}
export function useVisualPresentations(id:string){
 return useQuery({queryKey:[...key(id),"presentations"],queryFn:()=>apiRequest<VisualPresentationRead[]>(`${root}/${id}/visual-presentations`),enabled:!!id,retry:false});
}
export function useVisualResponses(id:string){
 return useQuery({queryKey:[...key(id),"visual-responses"],queryFn:()=>apiRequest<VisualResponseRead[]>(`${root}/${id}/visual-responses`),enabled:!!id});
}
export function useSaveVisualResponse(id:string){
 const qc=useQueryClient();
 return useMutation({mutationFn:({stimulusKey,choice}:{stimulusKey:string;choice:VisualChoiceEnum})=>
 apiRequest<VisualResponseRead>(`${root}/${id}/visual-responses/${encodeURIComponent(stimulusKey)}`,{method:"PUT",body:JSON.stringify({choice})}),
 onSuccess:()=>qc.invalidateQueries({queryKey:[...key(id),"visual-responses"]})});
}
export function useCompleteVisualAssessment(id:string){
 const qc=useQueryClient();
 return useMutation({mutationFn:()=>post<unknown>(`${root}/${id}/complete-visual`),onSuccess:()=>invalidate(qc,id)});
}
export function useBuildMultimodalProfile(id:string){
 const qc=useQueryClient();
 return useMutation({mutationFn:()=>post<UserPreferenceProfileResponse>(`${root}/${id}/build-profile`),onSuccess:()=>{invalidate(qc,id);qc.invalidateQueries({queryKey:[...key(id),"profile"]})}});
}
export function useUserPreferenceProfile(id:string){
 return useQuery({queryKey:[...key(id),"profile"],queryFn:()=>apiRequest<UserPreferenceProfileResponse>(`${root}/${id}/preference-profile`),enabled:!!id,retry:false});
}
export function useConfidenceProfile(id:string){
 return useQuery({queryKey:[...key(id),"confidence"],queryFn:()=>apiRequest<PreferenceConfidenceProfileResponse>(`${root}/${id}/confidence-profile`),enabled:!!id,retry:false});
}
export function useOverrideDimension(id:string){
 const qc=useQueryClient();
 return useMutation({mutationFn:({dimensionKey,value}:{dimensionKey:string;value:number})=>
 apiRequest<UserPreferenceProfileResponse>(`${root}/${id}/preference-profile/dimensions/${encodeURIComponent(dimensionKey)}`,{method:"PUT",body:JSON.stringify({value})}),
 onSuccess:()=>qc.invalidateQueries({queryKey:[...key(id),"profile"]})});
}
export function useConfirmProfile(id:string){
 const qc=useQueryClient();
 return useMutation({mutationFn:()=>post<UserPreferenceProfileResponse>(`${root}/${id}/confirm-profile`),
 onSuccess:()=>{invalidate(qc,id);qc.invalidateQueries({queryKey:[...key(id),"profile"]})}});
}
export function useImportanceProfile(id:string){
 return useQuery({queryKey:[...key(id),"importance"],queryFn:()=>apiRequest<ImportanceProfileResponse>(`${root}/${id}/importance-profile`),enabled:!!id,retry:false});
}
export function useCreateImportanceProfile(id:string){
 const qc=useQueryClient();
 return useMutation({mutationFn:(payload:ImportanceSelectionRequest)=>
 apiRequest<ImportanceProfileResponse>(`${root}/${id}/importance-profile`,{method:"POST",body:JSON.stringify(payload)}),
 onSuccess:()=>{invalidate(qc,id);qc.invalidateQueries({queryKey:[...key(id),"importance"]})}});
}
export function useUserNarrativeProfile(id:string){
 return useQuery({queryKey:[...key(id),"narrative"],queryFn:()=>apiRequest<UserNarrativeProfileResponse>(`${root}/${id}/narrative-profile`),enabled:!!id,retry:false});
}
export function useCreateNarrativeProfile(id:string){
 const qc=useQueryClient();
 return useMutation({mutationFn:(payload:NarrativeSelectionRequest)=>
 apiRequest<UserNarrativeProfileResponse>(`${root}/${id}/narrative-profile`,{method:"POST",body:JSON.stringify(payload)}),
 onSuccess:()=>{invalidate(qc,id);qc.invalidateQueries({queryKey:[...key(id),"narrative"]})}});
}
