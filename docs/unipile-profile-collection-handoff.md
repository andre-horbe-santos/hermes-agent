# Handoff — coleta ampliada de perfis Unipile

Implementado no projeto Koncepto/Sales Signal:

- O enriquecimento usa `linkedin_sections` da API v1 para solicitar experiência,
  formação, idiomas, competências, certificações, voluntariado, projetos,
  recomendações e interesses.
- O retorno é normalizado em `profile_sections`, incluindo também os dados
  básicos disponíveis no perfil (headline/sobre, identificadores, fotos,
  localização, contagens e contatos quando fornecidos pelo provedor).
- O dossiê é persistido em `ssk_lead_profiles.profile_data` como JSONB, sem
  sobrecarregar `ssk_leads`.
- Antes de ativar em produção, executar
  `scripts/sales_signal/migration_lead_profiles.sql` no Supabase.

Documentação oficial consultada:

- https://developer.unipile.com/v2.0/reference/getuserprofile
- https://developer.unipile.com/v2.0/docs/linkedin-fetch-users-profiles
- https://developer.unipile.com/v2.0/docs/migration-users-api
- https://developer.unipile.com/v2.0/docs/provider-limits-and-restrictions

Observação: esta versão solicita os nomes sem prefixo (`experience`, `skills`,
etc.) porque o código usa o endpoint Unipile v1; na documentação v2 os mesmos
blocos aparecem como `linkedin_experience`, `linkedin_skills` etc. em
`with_sections`.
