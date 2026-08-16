import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "./client";
import { API_BASE_URL } from "../constants";
import {
  CatalogCarpetListResponse,
  CatalogCarpetDetailRead,
  CarpetMotifAssociationRead,
  CarpetStoryAssociationRead,
  VisualStyleMatchResultResponse,
  NarrativeAffinityDetailRead,
  NarrativeAffinityResultRead,
  ListCatalogCarpetsParams,
  PrimaryImageSummary,
  CarpetStyleProfileRead,
  BrandRead,
  BrandListResponse
} from "../types/api";

export const catalogKeys = {
  all: ["catalog"] as const,
  brands: () => [...catalogKeys.all, "brands"] as const,
  brand: (brandKey: string) => [...catalogKeys.all, "brand", brandKey] as const,
  carpets: (params?: Record<string, unknown>) => [...catalogKeys.all, "carpets", params] as const,
  carpet: (idOrSku: string) => [...catalogKeys.all, "carpet", idOrSku] as const,
  motifs: (idOrSku: string) => [...catalogKeys.all, "motifs", idOrSku] as const,
  storyAssociations: (idOrSku: string) => [...catalogKeys.all, "story-associations", idOrSku] as const,
  styleMatches: (assessmentId: string) => [...catalogKeys.all, "style-matches", assessmentId] as const,
  styleMatch: (assessmentId: string, matchId: string) => [...catalogKeys.all, "style-match", assessmentId, matchId] as const,
  narrativeAffinities: (assessmentId: string) => [...catalogKeys.all, "narrative-affinities", assessmentId] as const,
  narrativeAffinity: (assessmentId: string, affinityId: string) => [...catalogKeys.all, "narrative-affinity", assessmentId, affinityId] as const
};

export function useBrands(verifiedOnly: boolean = false) {
  return useQuery({
    queryKey: [...catalogKeys.brands(), { verifiedOnly }],
    queryFn: () => apiRequest<BrandListResponse>(`/api/v1/brands${verifiedOnly ? "?verified_only=true" : ""}`)
  });
}

export function useBrand(brandKey: string) {
  return useQuery({
    queryKey: catalogKeys.brand(brandKey),
    queryFn: () => apiRequest<BrandRead>(`/api/v1/brands/${brandKey}`),
    enabled: Boolean(brandKey)
  });
}

export function useCatalogCarpets(params?: ListCatalogCarpetsParams) {
  const queryParams = new URLSearchParams();
  if (params?.limit) queryParams.set("limit", String(params.limit));
  if (params?.offset) queryParams.set("offset", String(params.offset));
  if (params?.manufacturer) queryParams.set("manufacturer", params.manufacturer);
  if (params?.brand_key) queryParams.set("brand_key", params.brand_key);
  if (params?.collection) queryParams.set("collection", params.collection);
  if (params?.material) queryParams.set("material", params.material);
  if (params?.style_label) queryParams.set("style_label", params.style_label);

  const queryString = queryParams.toString();
  const endpoint = `/api/v1/catalog/carpets${queryString ? `?${queryString}` : ""}`;

  return useQuery({
    queryKey: catalogKeys.carpets(params),
    queryFn: () => apiRequest<CatalogCarpetListResponse>(endpoint)
  });
}

export function useCatalogCarpet(idOrSku: string) {
  return useQuery({
    queryKey: catalogKeys.carpet(idOrSku),
    queryFn: () => apiRequest<CatalogCarpetDetailRead>(`/api/v1/catalog/carpets/${idOrSku}`),
    enabled: Boolean(idOrSku)
  });
}

export function useCarpetMotifs(idOrSku: string) {
  return useQuery({
    queryKey: catalogKeys.motifs(idOrSku),
    queryFn: () => apiRequest<CarpetMotifAssociationRead[]>(`/api/v1/catalog/carpets/${idOrSku}/motifs`),
    enabled: Boolean(idOrSku)
  });
}

export function resolveCarpetImageUrl(carpetId?: string | null, primaryImage?: PrimaryImageSummary | null): string | null {
  if (!primaryImage) return null;
  if (primaryImage.image_id && carpetId) {
    return `${API_BASE_URL}/api/v1/carpets/${carpetId}/images/${primaryImage.image_id}/content`;
  }
  if (primaryImage.file_path) {
    return `${API_BASE_URL}/static/${primaryImage.file_path}`;
  }
  return null;
}

export function useCarpetStyleDna(carpetId?: string, imageId?: string) {
  return useQuery({
    queryKey: ["style-dna", carpetId, imageId],
    queryFn: () => apiRequest<CarpetStyleProfileRead>(`/api/v1/carpets/${carpetId}/images/${imageId}/style-dna`),
    enabled: Boolean(carpetId && imageId)
  });
}

export function useCarpetStoryAssociations(idOrSku: string) {
  return useQuery({
    queryKey: catalogKeys.storyAssociations(idOrSku),
    queryFn: () => apiRequest<CarpetStoryAssociationRead[]>(`/api/v1/catalog/carpets/${idOrSku}/story-associations`),
    enabled: Boolean(idOrSku)
  });
}

// ---------------------------------------------------------
// VISUAL STYLE MATCH HOOKS
// ---------------------------------------------------------
export function useCreateStyleMatch(assessmentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      user_preference_profile_id: string;
      carpet_style_profile_id: string;
      importance_profile_id?: string | null;
    }) =>
      apiRequest<VisualStyleMatchResultResponse>(
        `/api/v1/preference-assessments/${assessmentId}/style-matches`,
        {
          method: "POST",
          body: JSON.stringify(payload)
        }
      ),
    onSuccess: (data) => {
      queryClient.setQueryData(catalogKeys.styleMatch(assessmentId, data.id), data);
      queryClient.invalidateQueries({ queryKey: catalogKeys.styleMatches(assessmentId) });
    }
  });
}

export function useStyleMatch(assessmentId: string, matchId: string) {
  return useQuery({
    queryKey: catalogKeys.styleMatch(assessmentId, matchId),
    queryFn: () =>
      apiRequest<VisualStyleMatchResultResponse>(
        `/api/v1/preference-assessments/${assessmentId}/style-matches/${matchId}`
      ),
    enabled: Boolean(assessmentId && matchId)
  });
}

export function useStyleMatches(assessmentId: string) {
  return useQuery({
    queryKey: catalogKeys.styleMatches(assessmentId),
    queryFn: () =>
      apiRequest<VisualStyleMatchResultResponse[]>(
        `/api/v1/preference-assessments/${assessmentId}/style-matches`
      ),
    enabled: Boolean(assessmentId)
  });
}

// ---------------------------------------------------------
// NARRATIVE AFFINITY HOOKS
// ---------------------------------------------------------
export function useCreateNarrativeAffinity(assessmentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { carpet_id: string }) =>
      apiRequest<NarrativeAffinityDetailRead>(
        `/api/v1/preference-assessments/${assessmentId}/narrative-affinities`,
        {
          method: "POST",
          body: JSON.stringify(payload)
        }
      ),
    onSuccess: (data) => {
      queryClient.setQueryData(catalogKeys.narrativeAffinity(assessmentId, data.result.id), data);
      queryClient.invalidateQueries({ queryKey: catalogKeys.narrativeAffinities(assessmentId) });
    }
  });
}

export function useNarrativeAffinity(assessmentId: string, affinityId: string) {
  return useQuery({
    queryKey: catalogKeys.narrativeAffinity(assessmentId, affinityId),
    queryFn: () =>
      apiRequest<NarrativeAffinityDetailRead>(
        `/api/v1/preference-assessments/${assessmentId}/narrative-affinities/${affinityId}`
      ),
    enabled: Boolean(assessmentId && affinityId)
  });
}

export function useNarrativeAffinities(assessmentId: string) {
  return useQuery({
    queryKey: catalogKeys.narrativeAffinities(assessmentId),
    queryFn: () =>
      apiRequest<NarrativeAffinityResultRead[]>(
        `/api/v1/preference-assessments/${assessmentId}/narrative-affinities`
      ),
    enabled: Boolean(assessmentId)
  });
}
