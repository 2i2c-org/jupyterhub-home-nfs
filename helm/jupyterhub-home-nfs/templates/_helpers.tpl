{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "jupyterhub-home-nfs.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

# Borrowed from https://github.com/2i2c-org/binderhub-service/blob/main/binderhub-service/templates/_helpers-names.tpl
{{- /*
    Renders to a prefix for the chart's resource names. This prefix is assumed to
    make the resource name cluster unique.
*/}}
{{- define "jupyterhub-home-nfs.fullname" -}}
    {{- /*
        We have implemented a trick to allow a parent chart depending on this
        chart to call these named templates.

        Caveats and notes:

            1. While parent charts can reference these, grandparent charts can't.
            2. Parent charts must not use an alias for this chart.
            3. There is no failsafe workaround to above due to
               https://github.com/helm/helm/issues/9214.
            4. .Chart is of its own type (*chart.Metadata) and needs to be casted
               using "toYaml | fromYaml" in order to be able to use normal helm
               template functions on it.
    */}}
    {{- $fullname_override := .Values.fullnameOverride }}
    {{- $name_override := .Values.nameOverride }}
    {{- if ne .Chart.Name "binderhub-service" }}
        {{- if .Values.jupyterhub }}
            {{- $fullname_override = .Values.jupyterhub.fullnameOverride }}
            {{- $name_override = .Values.jupyterhub.nameOverride }}
        {{- end }}
    {{- end }}

    {{- if eq (typeOf $fullname_override) "string" }}
        {{- $fullname_override }}
    {{- else }}
        {{- $name := $name_override | default "" }}
        {{- if contains $name .Release.Name }}
            {{- .Release.Name }}
        {{- else }}
            {{- .Release.Name }}-{{ $name }}
        {{- end }}
    {{- end }}
{{- end }}


{{/*
    Renders to a blank string or if the fullname template is truthy renders to it
    with an appended dash.
*/}}
{{- define "jupyterhub-home-nfs.fullname.dash" -}}
    {{- if (include "jupyterhub-home-nfs.fullname" .) }}
        {{- include "jupyterhub-home-nfs.fullname" . }}-
    {{- end }}
{{- end }}

{{- /* jupyterhub-home-nfs resources' default name */}}
{{- define "jupyterhub-home-nfs.home-nfs.fullname" -}}
    {{- include "jupyterhub-home-nfs.fullname.dash" . }}home-nfs
{{- end }}


{{/*
Common labels
*/}}
{{- define "jupyterhub-home-nfs.labels" -}}
helm.sh/chart: {{ include "jupyterhub-home-nfs.chart" . }}
{{ include "jupyterhub-home-nfs.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "jupyterhub-home-nfs.selectorLabels" -}}
app.kubernetes.io/name: {{ include "jupyterhub-home-nfs.home-nfs.fullname" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
