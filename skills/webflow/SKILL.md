---
name: webflow
description: Interact with Webflow sites, CMS collections, and content using the Webflow Data API v2. Manage pages, assets, and custom code programmatically.
triggers:
- webflow
- webflow api
- webflow cms
- webflow site
---

# Webflow API

Access Webflow sites and CMS content via the Data API v2.

## Authentication

Requires `WEBFLOW_API_KEY` environment variable with appropriate scopes.

```bash
curl -H "Authorization: Bearer $WEBFLOW_API_KEY" \
  -H "accept: application/json" \
  "https://api.webflow.com/v2/..."
```

## Common Scopes

| Scope | Access |
|-------|--------|
| `sites:read` | List and view sites |
| `sites:write` | Publish sites |
| `cms:read` | List collections and items |
| `cms:write` | Create/update/delete CMS items |
| `pages:read` | List and view pages |
| `pages:write` | Update page metadata |
| `custom_code:read` | View custom code |
| `custom_code:write` | Add/modify custom code |
| `assets:read` | List assets |
| `assets:write` | Upload assets |

## Sites

### List All Sites

```bash
curl -s -H "Authorization: Bearer $WEBFLOW_API_KEY" \
  -H "accept: application/json" \
  "https://api.webflow.com/v2/sites" | jq '.sites[] | {id, displayName, shortName}'
```

### Get Site Details

```bash
curl -s -H "Authorization: Bearer $WEBFLOW_API_KEY" \
  -H "accept: application/json" \
  "https://api.webflow.com/v2/sites/{site_id}" | jq '.'
```

### Publish Site

```bash
curl -s -X POST -H "Authorization: Bearer $WEBFLOW_API_KEY" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  "https://api.webflow.com/v2/sites/{site_id}/publish" \
  -d '{"publishToWebflowSubdomain": true}'
```

## CMS Collections

### List Collections

```bash
curl -s -H "Authorization: Bearer $WEBFLOW_API_KEY" \
  -H "accept: application/json" \
  "https://api.webflow.com/v2/sites/{site_id}/collections" \
  | jq '.collections[] | {id, displayName, slug}'
```

### Get Collection Schema

```bash
curl -s -H "Authorization: Bearer $WEBFLOW_API_KEY" \
  -H "accept: application/json" \
  "https://api.webflow.com/v2/collections/{collection_id}" \
  | jq '{displayName, slug, fields: [.fields[] | {id, slug, displayName, type, isRequired}]}'
```

### Create Collection

```bash
curl -s -X POST -H "Authorization: Bearer $WEBFLOW_API_KEY" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  "https://api.webflow.com/v2/sites/{site_id}/collections" \
  -d '{
    "displayName": "Blog Posts",
    "singularName": "Blog Post",
    "slug": "blog-posts"
  }'
```

## CMS Items

### List Items in Collection

```bash
curl -s -H "Authorization: Bearer $WEBFLOW_API_KEY" \
  -H "accept: application/json" \
  "https://api.webflow.com/v2/collections/{collection_id}/items" \
  | jq '.items[] | {id, fieldData}'
```

### Get Single Item

```bash
curl -s -H "Authorization: Bearer $WEBFLOW_API_KEY" \
  -H "accept: application/json" \
  "https://api.webflow.com/v2/collections/{collection_id}/items/{item_id}" \
  | jq '.'
```

### Create Item

```bash
curl -s -X POST -H "Authorization: Bearer $WEBFLOW_API_KEY" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  "https://api.webflow.com/v2/collections/{collection_id}/items" \
  -d '{
    "fieldData": {
      "name": "My New Item",
      "slug": "my-new-item",
      "custom-field": "value"
    }
  }'
```

### Update Item

```bash
curl -s -X PATCH -H "Authorization: Bearer $WEBFLOW_API_KEY" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  "https://api.webflow.com/v2/collections/{collection_id}/items/{item_id}" \
  -d '{
    "fieldData": {
      "custom-field": "updated value"
    }
  }'
```

### Publish Item

```bash
curl -s -X POST -H "Authorization: Bearer $WEBFLOW_API_KEY" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  "https://api.webflow.com/v2/collections/{collection_id}/items/publish" \
  -d '{"itemIds": ["item_id_1", "item_id_2"]}'
```

### Delete Item

```bash
curl -s -X DELETE -H "Authorization: Bearer $WEBFLOW_API_KEY" \
  -H "accept: application/json" \
  "https://api.webflow.com/v2/collections/{collection_id}/items/{item_id}"
```

## Pages

### List Pages

```bash
curl -s -H "Authorization: Bearer $WEBFLOW_API_KEY" \
  -H "accept: application/json" \
  "https://api.webflow.com/v2/sites/{site_id}/pages" \
  | jq '.pages[] | {id, title, slug}'
```

### Get Page Metadata

```bash
curl -s -H "Authorization: Bearer $WEBFLOW_API_KEY" \
  -H "accept: application/json" \
  "https://api.webflow.com/v2/pages/{page_id}" | jq '.'
```

### Update Page SEO

```bash
curl -s -X PATCH -H "Authorization: Bearer $WEBFLOW_API_KEY" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  "https://api.webflow.com/v2/pages/{page_id}" \
  -d '{
    "seo": {
      "title": "Page Title | Site Name",
      "description": "Meta description for SEO"
    }
  }'
```

## Assets

### List Assets

```bash
curl -s -H "Authorization: Bearer $WEBFLOW_API_KEY" \
  -H "accept: application/json" \
  "https://api.webflow.com/v2/sites/{site_id}/assets" \
  | jq '.assets[] | {id, displayName, url}'
```

## Custom Code

### Add Site-Wide Custom Code

```bash
curl -s -X PUT -H "Authorization: Bearer $WEBFLOW_API_KEY" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  "https://api.webflow.com/v2/sites/{site_id}/custom_code" \
  -d '{
    "scripts": [{
      "id": "script_id",
      "location": "header",
      "version": "1.0.0"
    }]
  }'
```

### Add Page-Specific Custom Code

```bash
curl -s -X PUT -H "Authorization: Bearer $WEBFLOW_API_KEY" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  "https://api.webflow.com/v2/pages/{page_id}/custom_code" \
  -d '{
    "scripts": [{
      "id": "script_id",
      "location": "footer",
      "version": "1.0.0"
    }]
  }'
```

## Error Handling

Common error codes:

| Code | Meaning |
|------|---------|
| `missing_scopes` | Token lacks required permissions |
| `not_found` | Resource doesn't exist |
| `rate_limit_exceeded` | Too many requests (wait and retry) |
| `validation_error` | Invalid request data |

## Rate Limits

- Default: 60 requests/minute
- Check `X-RateLimit-Remaining` header
- Back off when approaching limit

## Documentation

- [Webflow Data API v2](https://developers.webflow.com/data/reference)
- [CMS API Reference](https://developers.webflow.com/data/reference/cms)
- [Authentication Guide](https://developers.webflow.com/data/docs/getting-started-with-apps)
