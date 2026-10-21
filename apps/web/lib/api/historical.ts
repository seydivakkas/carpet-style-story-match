import {useMutation,useQuery} from "@tanstack/react-query";
import {apiRequest} from "./client";
import type {
 HistoricalReferenceDetailRead,HistoricalReferenceListResponse,HistoricalConnectionDetailRead,
 HistoricalConnectionCreateInput,ListHistoricalReferencesParams
} from "../types/api";

export function useHistoricalReferences(filters:ListHistoricalReferencesParams={}){
 const qs=new URLSearchParams();
 if(filters.institution || filters.museum) qs.set("institution",filters.institution||filters.museum||"");
 if(filters.region) qs.set("culture",filters.region);
 if(filters.limit) qs.set("limit",String(filters.limit));
 if(filters.offset) qs.set("offset",String(filters.offset));
 const suffix=qs.toString();
 return useQuery({queryKey:["historical-references",filters],queryFn:()=>
 apiRequest<HistoricalReferenceListResponse>(`/api/v1/historical-references${suffix?"?"+suffix:""}`)});
}
export function useHistoricalReference(idOrKey:string){
 return useQuery({queryKey:["historical-reference",idOrKey],queryFn:()=>apiRequest<HistoricalReferenceDetailRead>(
 `/api/v1/historical-references/${encodeURIComponent(idOrKey)}`),enabled:!!idOrKey});
}
export function useHistoricalConnection(id:string){
 return useQuery({queryKey:["historical-connection",id],queryFn:()=>apiRequest<HistoricalConnectionDetailRead>(
 `/api/v1/historical-connections/${encodeURIComponent(id)}`),enabled:!!id});
}
export function useCreateHistoricalConnection(){
 return useMutation({mutationFn:(payload:HistoricalConnectionCreateInput)=>
 apiRequest<HistoricalConnectionDetailRead>("/api/v1/historical-connections",{method:"POST",body:JSON.stringify(payload)})});
}
