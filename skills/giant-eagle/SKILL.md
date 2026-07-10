---
name: giant-eagle
description: Find Giant Eagle grocery products and ingredient substitutions for recipes using the website and the underlying product search API.
triggers:
- giant eagle
- grocery ingredients
- buy ingredients
- recipe shopping
- grocery search
---

# Giant Eagle Ingredient Search

Use this skill when you need to turn a recipe into Giant Eagle shopping links.

## What This Skill Covers

- Extracting ingredients from a recipe page
- Finding exact Giant Eagle matches when available
- Finding close substitutions when specialty ingredients are unavailable
- Building direct Giant Eagle product links and search links
- Using the product search API first, then falling back to browser-visible search links when needed

## Recommended Workflow

1. Read the recipe page and extract a normalized ingredient list.
2. Query the Giant Eagle product search API for each core ingredient.
3. Convert strong matches into direct product links.
4. If the API result is weak, ambiguous, or store-sensitive, add a storefront search link as a browser fallback.
5. If the exact product is unavailable, return the closest reasonable substitute and explain it.
6. Warn that availability varies by selected store.

## Step 1: Extract Ingredients from the Recipe

Use the browser content tools to capture the ingredient list from the recipe page.

Things to normalize while extracting:
- Remove quantities when searching (`4 x 150g salmon fillets` → `salmon`)
- Keep distinguishing adjectives when they matter (`purple potatoes`, `white wine vinegar`)
- Split optional pantry seasonings into separate searches if needed (`salt`, `white pepper`, `lemon juice`)
- Recognize likely substitutions for regional ingredients (`kūmara` → sweet potato)

## Step 2: Use the Product Search API First

Giant Eagle's web app queries a GraphQL API behind the storefront. For agent workflows, this is usually the fastest and most reliable first step because it returns structured results instead of browser-rendered page text.

### Endpoint

```text
https://core.shop.gianteagle.com/api/v2
```

### Required Request Headers

```bash
-H 'content-type: application/json;charset=utf-8' \
-H 'accept: application/json, text/plain, */*' \
-H 'x-hl-app: grocery' \
-H 'x-hl-client: web' \
-H 'x-hl-referrer: https://www.gianteagle.com/grocery/search' \
-H 'x-hl-request-id: some-unique-id' \
-H 'x-hl-version: 300f0b2a7bb04c1'
```

### Product Query

```graphql
query GetProducts(
  $cursor: String
  $count: Int
  $filters: ProductFilters
  $store: StoreInput!
  $sort: ProductSortKey
) {
  products(
    first: $count
    after: $cursor
    filters: $filters
    store: $store
    sort: $sort
  ) {
    edges {
      cursor
      node {
        sku
        name
        brand
      }
    }
    totalCount
    queryId
    responseId
  }
}
```

### Reliable Minimal Request

Use the virtual catalog when you do not have a real store selected:

```bash
curl -s 'https://core.shop.gianteagle.com/api/v2' \
  -H 'content-type: application/json;charset=utf-8' \
  -H 'accept: application/json, text/plain, */*' \
  -H 'x-hl-app: grocery' \
  -H 'x-hl-client: web' \
  -H 'x-hl-referrer: https://www.gianteagle.com/grocery/search' \
  -H 'x-hl-request-id: giant-eagle-skill-demo' \
  -H 'x-hl-version: 300f0b2a7bb04c1' \
  --data-binary '{
    "operationName": "GetProducts",
    "query": "query GetProducts($count:Int,$filters:ProductFilters,$store:StoreInput!,$sort:ProductSortKey){products(first:$count,filters:$filters,store:$store,sort:$sort){edges{node{sku name brand}} totalCount}}",
    "variables": {
      "count": 10,
      "filters": {
        "query": "salmon",
        "circular": false
      },
      "store": {
        "storeCode": "VIRTUAL"
      },
      "sort": "bestMatch"
    }
  }'
```

### Why This Helps

The browser-rendered page can be noisy or incomplete in agent browsing tools. The GraphQL response is much easier to parse programmatically and gives you:
- SKU
- product name
- brand
- result counts

Once you have a SKU, build a stable product link:

```text
https://www.gianteagle.com/grocery/search/product/SKU
```


## Step 3: Fall Back to the Website Search UI

After you have candidate products from GraphQL, use storefront URLs for user-facing output and as a fallback when the API result is unclear.

- Search URL pattern: `https://www.gianteagle.com/grocery/search?q=QUERY`
- Direct product URL pattern: `https://www.gianteagle.com/grocery/search/product/SKU`

Examples:

- `https://www.gianteagle.com/grocery/search?q=salmon`
- `https://www.gianteagle.com/grocery/search?q=white%20wine%20vinegar`
- `https://www.gianteagle.com/grocery/search/product/00030034937669`

Use the browser/search-link fallback when:
- the ingredient is broad and the user may want to choose among variants
- the API returns weak or noisy matches
- the item is highly store-dependent, such as fresh seafood, specialty produce, or alcohol
- you want a durable user-facing link rather than a raw API result

## Search Strategy for Recipe Ingredients

### Exact Match First

Start with the obvious base ingredient:
- `salmon`
- `shallot`
- `red cabbage`
- `white wine vinegar`
- `unsalted butter`

### Narrow with Distinguishing Terms

If results are too broad, search with important descriptors:
- `purple potatoes`
- `purple sweet potato`
- `rose wine`
- `canola oil`
- `white pepper`

### Use Substitutions for Regional or Premium Ingredients

Some recipe ingredients may not exist exactly at Giant Eagle. In those cases, pick the closest practical substitute and say so explicitly.

Examples:
- `Ōra King salmon` → farmed salmon fillet or premium salmon fillet
- `purple kūmara` → purple sweet potato / Stokes purple sweet potato
- specific winery rosé → a dry rosé available at Giant Eagle

### Prefer Product Links Over Search Links

If the API returns a clear best result, give the product link.

If the ingredient is broad or store-dependent, include a search link too.

Good candidates for direct product links:
- butter
- vinegar
- oil
- spices
- lemons

Good candidates for search links:
- fresh fish
- specialty produce
- alcohol

## Example Output Pattern

```markdown
- **Salmon (substitute for Ōra King):** [Giant Eagle Salmon, Farmed, Fillet, Chile](https://www.gianteagle.com/grocery/search/product/00208598000000)
- **Purple potatoes:** [Tasteful Selections Baby Potatoes, Purple Passion](https://www.gianteagle.com/grocery/search/product/00030034937942)
- **Rosé wine:** [Search rosé wine](https://www.gianteagle.com/grocery/search?q=rose%20wine)
```

## Important Caveats

- Giant Eagle results depend on the selected store; the virtual catalog is a useful fallback but not a guarantee of local availability.
- Alcohol availability may vary by state and store.
- Fresh seafood and produce can change often, so search links may age better than locking onto a single SKU.
- For recipe help, users usually want practical shopping guidance, not ingredient purity. Favor useful substitutions over saying "not found."

## Summary

Use this order of operations:
1. Extract recipe ingredients
2. Query `https://core.shop.gianteagle.com/api/v2`
3. Convert strong matches into direct product links
4. Fall back to `gianteagle.com/grocery/search?q=...` when the result is ambiguous or user choice matters
5. Provide substitutions and search links for specialty ingredients
