-- Dietary Flags Validation Queries
-- Use these queries to validate the dietary flags implementation

-- =============================================================================
-- 1. BASIC VALIDATION QUERIES
-- =============================================================================

-- Check coverage
SELECT 
    COUNT(*) as total_items,
    COUNT(CASE WHEN dietary_flags IS NOT NULL THEN 1 END) as items_with_flags,
    ROUND(COUNT(CASE WHEN dietary_flags IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2) as coverage_percentage
FROM food_items;

-- Check MyPlate distribution
SELECT 
    dietary_flags->>'myplate_food_group' as food_group,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) as percentage
FROM food_items 
WHERE dietary_flags IS NOT NULL
GROUP BY dietary_flags->>'myplate_food_group'
ORDER BY count DESC;

-- =============================================================================
-- 2. FDA NUTRITIONAL CLAIMS VALIDATION
-- =============================================================================

-- Top FDA claims
SELECT 
    jsonb_array_elements_text(dietary_flags->'fda_nutritional_claims') as claim,
    COUNT(*) as claim_count
FROM food_items 
WHERE dietary_flags->'fda_nutritional_claims' IS NOT NULL
GROUP BY claim
ORDER BY claim_count DESC;

-- Items with multiple nutritional claims (high quality)
SELECT 
    description,
    food_category,
    jsonb_array_length(dietary_flags->'fda_nutritional_claims') as claims_count,
    dietary_flags->'fda_nutritional_claims' as claims
FROM food_items 
WHERE jsonb_array_length(dietary_flags->'fda_nutritional_claims') >= 4
ORDER BY claims_count DESC
LIMIT 10;

-- =============================================================================
-- 3. ALLERGEN DETECTION VALIDATION  
-- =============================================================================

-- Allergen detection summary
SELECT 
    jsonb_array_elements_text(dietary_flags->'potential_allergens') as allergen,
    COUNT(*) as detection_count
FROM food_items 
WHERE dietary_flags->'potential_allergens' IS NOT NULL 
  AND jsonb_array_length(dietary_flags->'potential_allergens') > 0
GROUP BY allergen
ORDER BY detection_count DESC;

-- Items with multiple allergens
SELECT 
    description,
    food_category,
    jsonb_array_length(dietary_flags->'potential_allergens') as allergen_count,
    dietary_flags->'potential_allergens' as allergens
FROM food_items 
WHERE jsonb_array_length(dietary_flags->'potential_allergens') >= 2
ORDER BY allergen_count DESC
LIMIT 10;

-- =============================================================================
-- 4. QUALITY ASSURANCE QUERIES
-- =============================================================================

-- Dairy products should be classified as 'dairy'
SELECT COUNT(*) as dairy_items_correctly_classified
FROM food_items 
WHERE food_category = 'Dairy and Egg Products' 
  AND dietary_flags->>'myplate_food_group' = 'dairy';

-- Verify low sodium classification (should have sodium < 140mg)
SELECT 
    description,
    get_nutrient_amount(nutrients, 'Sodium, Na') as sodium_mg
FROM food_items 
WHERE dietary_flags->'fda_nutritional_claims' ? 'low_sodium'
  AND nutrients IS NOT NULL
  AND get_nutrient_amount(nutrients, 'Sodium, Na') >= 140
LIMIT 5; -- Should return 0 rows for correct implementation

-- Verify high protein classification (should have protein >= 10g)
SELECT 
    description,
    get_nutrient_amount(nutrients, 'Protein') as protein_g
FROM food_items 
WHERE dietary_flags->'fda_nutritional_claims' ? 'high_protein'
  AND nutrients IS NOT NULL
  AND get_nutrient_amount(nutrients, 'Protein') < 10
LIMIT 5; -- Should return 0 rows for correct implementation

-- =============================================================================
-- 5. MANUAL REVIEW QUERIES
-- =============================================================================

-- Items that might need manual review (contradictory classifications)
SELECT 
    description,
    food_category,
    dietary_flags->>'myplate_food_group' as myplate_group,
    dietary_flags->'fda_nutritional_claims' as claims
FROM food_items 
WHERE (
    -- Sweets categorized as healthy
    (food_category ILIKE '%sweets%' AND dietary_flags->'fda_nutritional_claims' ? 'low_calorie')
    OR
    -- Fats categorized as low fat
    (food_category ILIKE '%fats%' AND dietary_flags->'fda_nutritional_claims' ? 'low_fat')
    OR
    -- Processed foods with many health claims
    (food_category ILIKE '%mixed%' AND jsonb_array_length(dietary_flags->'fda_nutritional_claims') >= 5)
)
LIMIT 10;

-- =============================================================================
-- 6. SEARCH AND QUERY EXAMPLES
-- =============================================================================

-- Find low sodium, high protein foods in vegetables group
SELECT 
    description,
    food_category,
    dietary_flags->'fda_nutritional_claims' as claims
FROM food_items 
WHERE dietary_flags->>'myplate_food_group' = 'vegetables'
  AND dietary_flags->'fda_nutritional_claims' ? 'low_sodium'
  AND dietary_flags->'fda_nutritional_claims' ? 'high_protein'
LIMIT 10;

-- Find dairy-free protein sources  
SELECT 
    description,
    food_category,
    dietary_flags->'potential_allergens' as allergens
FROM food_items 
WHERE dietary_flags->>'myplate_food_group' = 'protein'
  AND NOT (dietary_flags->'potential_allergens' ? 'milk')
  AND dietary_flags->'fda_nutritional_claims' ? 'high_protein'
LIMIT 10;

-- Find high-fiber grains without wheat allergens
SELECT 
    description,
    food_category,
    dietary_flags->'fda_nutritional_claims' as claims,
    dietary_flags->'potential_allergens' as allergens
FROM food_items 
WHERE dietary_flags->>'myplate_food_group' = 'grains'
  AND dietary_flags->'fda_nutritional_claims' ? 'high_fiber'
  AND NOT (dietary_flags->'potential_allergens' ? 'wheat')
LIMIT 10;