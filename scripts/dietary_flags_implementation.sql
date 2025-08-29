-- Dietary Flags Implementation for Food Items
-- Based on FDA/USDA Authoritative Sources
-- Author: Claude Code
-- Date: 2025-08-29

-- =============================================================================
-- HELPER FUNCTIONS FOR DIETARY FLAGS IMPLEMENTATION
-- =============================================================================

-- Function to extract nutrient value by name from nutrients JSONB
CREATE OR REPLACE FUNCTION get_nutrient_amount(nutrients JSONB, nutrient_name TEXT)
RETURNS NUMERIC AS $$
BEGIN
    RETURN (
        SELECT (elem->>'amount')::NUMERIC
        FROM jsonb_array_elements(nutrients) AS elem
        WHERE LOWER(elem->>'name') = LOWER(nutrient_name)
        LIMIT 1
    );
END;
$$ LANGUAGE plpgsql;

-- Function to extract nutrient value by nutrient number from nutrients JSONB
CREATE OR REPLACE FUNCTION get_nutrient_by_number(nutrients JSONB, nutrient_number TEXT)
RETURNS NUMERIC AS $$
BEGIN
    RETURN (
        SELECT (elem->>'amount')::NUMERIC
        FROM jsonb_array_elements(nutrients) AS elem
        WHERE elem->>'nutrient_number' = nutrient_number
        LIMIT 1
    );
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- MYPLATE FOOD GROUP MAPPING FUNCTION
-- Based on USDA MyPlate Guidelines
-- =============================================================================

CREATE OR REPLACE FUNCTION map_to_myplate_group(food_category TEXT)
RETURNS TEXT AS $$
BEGIN
    -- Direct mapping from USDA food categories to MyPlate food groups
    RETURN CASE
        -- VEGETABLES GROUP
        WHEN LOWER(food_category) LIKE '%vegetables%' THEN 'vegetables'
        WHEN LOWER(food_category) LIKE '%legume%' THEN 'vegetables'  -- Legumes count as vegetables in MyPlate
        
        -- FRUITS GROUP  
        WHEN LOWER(food_category) LIKE '%fruits%' THEN 'fruits'
        WHEN LOWER(food_category) LIKE '%fruit juice%' THEN 'fruits'
        
        -- GRAINS GROUP
        WHEN LOWER(food_category) LIKE '%cereal%' THEN 'grains'
        WHEN LOWER(food_category) LIKE '%grain%' THEN 'grains'
        WHEN LOWER(food_category) LIKE '%pasta%' THEN 'grains'
        WHEN LOWER(food_category) LIKE '%baked products%' THEN 'grains'
        WHEN LOWER(food_category) LIKE '%breakfast cereals%' THEN 'grains'
        WHEN LOWER(food_category) LIKE '%rice%' THEN 'grains'
        
        -- PROTEIN GROUP
        WHEN LOWER(food_category) LIKE '%beef%' THEN 'protein'
        WHEN LOWER(food_category) LIKE '%pork%' THEN 'protein'
        WHEN LOWER(food_category) LIKE '%poultry%' THEN 'protein'
        WHEN LOWER(food_category) LIKE '%lamb%' THEN 'protein'
        WHEN LOWER(food_category) LIKE '%sausage%' THEN 'protein'
        WHEN LOWER(food_category) LIKE '%luncheon%' THEN 'protein'
        WHEN LOWER(food_category) LIKE '%fish%' THEN 'protein'
        WHEN LOWER(food_category) LIKE '%seafood%' THEN 'protein'
        WHEN LOWER(food_category) LIKE '%finfish%' THEN 'protein'
        WHEN LOWER(food_category) LIKE '%shellfish%' THEN 'protein'
        WHEN LOWER(food_category) LIKE '%nut%' THEN 'protein'
        WHEN LOWER(food_category) LIKE '%seed%' THEN 'protein'
        WHEN LOWER(food_category) LIKE '%egg%' THEN 'protein'
        
        -- DAIRY GROUP
        WHEN LOWER(food_category) LIKE '%dairy%' THEN 'dairy'
        WHEN LOWER(food_category) LIKE '%milk%' THEN 'dairy'
        WHEN LOWER(food_category) LIKE '%cheese%' THEN 'dairy'
        WHEN LOWER(food_category) LIKE '%yogurt%' THEN 'dairy'
        
        -- UNCATEGORIZED (doesn't fit clearly into MyPlate categories)
        ELSE 'other'
    END;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- FDA NUTRITIONAL CLASSIFICATIONS FUNCTION
-- Based on FDA Code of Federal Regulations Title 21
-- =============================================================================

CREATE OR REPLACE FUNCTION calculate_fda_nutritional_flags(nutrients JSONB, serving_size NUMERIC)
RETURNS JSONB AS $$
DECLARE
    flags JSONB := '[]'::JSONB;
    sodium_mg NUMERIC;
    fat_g NUMERIC;
    fiber_g NUMERIC;
    protein_g NUMERIC;
    calories NUMERIC;
    
    -- FDA Reference Daily Values and thresholds
    -- Based on 21 CFR 101.54 and 21 CFR 101.62
    low_sodium_threshold CONSTANT NUMERIC := 140; -- mg per serving
    low_fat_threshold CONSTANT NUMERIC := 3; -- g per serving
    good_source_fiber_threshold CONSTANT NUMERIC := 2.5; -- g per serving (10% DV)
    high_protein_threshold CONSTANT NUMERIC := 10; -- g per serving (20% DV)
    
BEGIN
    -- Extract key nutrients (use both name matching and nutrient numbers)
    sodium_mg := COALESCE(get_nutrient_amount(nutrients, 'Sodium, Na'), 
                         get_nutrient_by_number(nutrients, '307'), 0);
    
    fat_g := COALESCE(get_nutrient_amount(nutrients, 'Total lipid (fat)'),
                     get_nutrient_by_number(nutrients, '204'), 0);
    
    fiber_g := COALESCE(get_nutrient_amount(nutrients, 'Fiber, total dietary'),
                       get_nutrient_by_number(nutrients, '291'), 0);
    
    protein_g := COALESCE(get_nutrient_amount(nutrients, 'Protein'),
                         get_nutrient_by_number(nutrients, '203'), 0);
    
    calories := COALESCE(get_nutrient_amount(nutrients, 'Energy'),
                        get_nutrient_by_number(nutrients, '208'), 0);
    
    -- Apply FDA classifications
    
    -- Low Sodium: Less than 140mg per serving (21 CFR 101.62(a)(1))
    IF sodium_mg < low_sodium_threshold THEN
        flags := flags || '"low_sodium"'::JSONB;
    END IF;
    
    -- Low Fat: Less than 3g per serving (21 CFR 101.62(b)(1))  
    IF fat_g < low_fat_threshold THEN
        flags := flags || '"low_fat"'::JSONB;
    END IF;
    
    -- Good Source of Fiber: 2.5g or more per serving (10% DV, 21 CFR 101.54(c))
    IF fiber_g >= good_source_fiber_threshold THEN
        flags := flags || '"good_source_fiber"'::JSONB;
    END IF;
    
    -- High Fiber: 5g or more per serving (20% DV, 21 CFR 101.54(c))
    IF fiber_g >= 5 THEN
        flags := flags || '"high_fiber"'::JSONB;
    END IF;
    
    -- High Protein: 10g or more per serving (20% DV, 21 CFR 101.54(c))
    IF protein_g >= high_protein_threshold THEN
        flags := flags || '"high_protein"'::JSONB;
    END IF;
    
    -- Calorie classifications (21 CFR 101.60)
    IF calories <= 5 THEN
        flags := flags || '"calorie_free"'::JSONB;
    ELSIF calories <= 40 THEN
        flags := flags || '"low_calorie"'::JSONB;
    END IF;
    
    -- Fat-free: Less than 0.5g fat per serving (21 CFR 101.62(b)(1))
    IF fat_g < 0.5 THEN
        flags := flags || '"fat_free"'::JSONB;
    END IF;
    
    -- Sodium-free: Less than 5mg per serving (21 CFR 101.61(a)(1))
    IF sodium_mg < 5 THEN
        flags := flags || '"sodium_free"'::JSONB;
    END IF;
    
    RETURN flags;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- FDA ALLERGEN DETECTION FUNCTION  
-- Based on FDA's 9 Major Food Allergens (FALCPA + FASTER Act)
-- =============================================================================

CREATE OR REPLACE FUNCTION detect_fda_allergens(ingredients TEXT, description TEXT)
RETURNS JSONB AS $$
DECLARE
    allergens JSONB := '[]'::JSONB;
    search_text TEXT;
BEGIN
    -- Combine ingredients and description for comprehensive search
    search_text := LOWER(COALESCE(ingredients, '') || ' ' || COALESCE(description, ''));
    
    -- Return empty array if no text to search
    IF LENGTH(TRIM(search_text)) = 0 THEN
        RETURN allergens;
    END IF;
    
    -- FDA's 9 Major Food Allergens (FALCPA + FASTER Act 2021)
    
    -- 1. Milk and dairy products
    IF search_text ~ '\y(milk|dairy|cheese|yogurt|butter|cream|casein|whey|lactose)\y' THEN
        allergens := allergens || '"milk"'::JSONB;
    END IF;
    
    -- 2. Eggs
    IF search_text ~ '\y(egg|eggs|albumin|lecithin)\y' THEN
        allergens := allergens || '"eggs"'::JSONB;
    END IF;
    
    -- 3. Fish
    IF search_text ~ '\y(fish|salmon|tuna|cod|bass|trout|halibut|sardine|anchovy)\y' THEN
        allergens := allergens || '"fish"'::JSONB;
    END IF;
    
    -- 4. Shellfish  
    IF search_text ~ '\y(shrimp|lobster|crab|clam|mussel|oyster|scallop|shellfish)\y' THEN
        allergens := allergens || '"shellfish"'::JSONB;
    END IF;
    
    -- 5. Tree nuts (include both specific nuts and general "nuts" term)
    IF search_text ~ '\y(nuts|almond|walnut|pecan|cashew|pistachio|brazil|hazelnut|macadamia|pine nut)\y' THEN
        allergens := allergens || '"tree_nuts"'::JSONB;
    END IF;
    
    -- 6. Peanuts
    IF search_text ~ '\y(peanut|groundnut)\y' THEN
        allergens := allergens || '"peanuts"'::JSONB;
    END IF;
    
    -- 7. Wheat
    IF search_text ~ '\y(wheat|flour|gluten|bulgur|durum|semolina|spelt|farro)\y' THEN
        allergens := allergens || '"wheat"'::JSONB;
    END IF;
    
    -- 8. Soybeans
    IF search_text ~ '\y(soy|soybean|tofu|tempeh|miso|soya)\y' THEN
        allergens := allergens || '"soybeans"'::JSONB;
    END IF;
    
    -- 9. Sesame (added by FASTER Act 2021)
    IF search_text ~ '\y(sesame|tahini|halvah|benne)\y' THEN
        allergens := allergens || '"sesame"'::JSONB;
    END IF;
    
    RETURN allergens;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- COMPREHENSIVE DIETARY FLAGS FUNCTION
-- Combines all classifications with proper data source attribution
-- =============================================================================

CREATE OR REPLACE FUNCTION generate_dietary_flags(
    food_category TEXT,
    nutrients JSONB,
    serving_size NUMERIC,
    ingredients TEXT,
    description TEXT
) RETURNS JSONB AS $$
DECLARE
    result JSONB := '{}'::JSONB;
    myplate_group TEXT;
    nutritional_flags JSONB;
    detected_allergens JSONB;
    
BEGIN
    -- MyPlate food group classification
    myplate_group := map_to_myplate_group(food_category);
    result := jsonb_set(result, '{myplate_food_group}', to_jsonb(myplate_group));
    
    -- FDA nutritional classifications
    IF nutrients IS NOT NULL THEN
        nutritional_flags := calculate_fda_nutritional_flags(nutrients, serving_size);
        result := jsonb_set(result, '{fda_nutritional_claims}', nutritional_flags);
    ELSE
        result := jsonb_set(result, '{fda_nutritional_claims}', '[]'::JSONB);
    END IF;
    
    -- FDA allergen detection
    detected_allergens := detect_fda_allergens(ingredients, description);
    result := jsonb_set(result, '{potential_allergens}', detected_allergens);
    
    -- Data source attribution and disclaimers
    result := jsonb_set(result, '{data_sources}', 
        '{"myplate_mapping": "USDA MyPlate Guidelines", 
          "nutritional_claims": "FDA CFR Title 21", 
          "allergen_detection": "FDA FALCPA/FASTER Act"}'::JSONB);
    
    result := jsonb_set(result, '{disclaimers}', 
        jsonb_build_object(
            'allergen_disclaimer', 'Allergen detection based on text parsing. Not a substitute for official allergen labeling.',
            'nutritional_disclaimer', 'Nutritional claims calculated from available nutrient data. Verify with official product labeling.',
            'last_updated', CURRENT_DATE::TEXT
        ));
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- MAIN UPDATE FUNCTION
-- Updates all food items with new dietary flags
-- =============================================================================

CREATE OR REPLACE FUNCTION update_all_dietary_flags()
RETURNS TABLE(
    updated_count BIGINT,
    myplate_vegetables BIGINT,
    myplate_fruits BIGINT,
    myplate_grains BIGINT,
    myplate_protein BIGINT,
    myplate_dairy BIGINT,
    myplate_other BIGINT,
    low_sodium_count BIGINT,
    low_fat_count BIGINT,
    high_fiber_count BIGINT,
    high_protein_count BIGINT,
    potential_allergens_detected BIGINT
) AS $$
DECLARE
    total_updated BIGINT := 0;
    stats_record RECORD;
BEGIN
    -- Update dietary_flags for all food items
    UPDATE food_items 
    SET dietary_flags = generate_dietary_flags(
            food_category,
            nutrients,
            serving_size,
            ingredients,
            description
        ),
        last_updated = CURRENT_TIMESTAMP
    WHERE TRUE; -- Update all records
    
    GET DIAGNOSTICS total_updated = ROW_COUNT;
    
    -- Generate statistics
    SELECT 
        total_updated as updated_count,
        SUM(CASE WHEN dietary_flags->>'myplate_food_group' = 'vegetables' THEN 1 ELSE 0 END) as myplate_vegetables,
        SUM(CASE WHEN dietary_flags->>'myplate_food_group' = 'fruits' THEN 1 ELSE 0 END) as myplate_fruits,
        SUM(CASE WHEN dietary_flags->>'myplate_food_group' = 'grains' THEN 1 ELSE 0 END) as myplate_grains,
        SUM(CASE WHEN dietary_flags->>'myplate_food_group' = 'protein' THEN 1 ELSE 0 END) as myplate_protein,
        SUM(CASE WHEN dietary_flags->>'myplate_food_group' = 'dairy' THEN 1 ELSE 0 END) as myplate_dairy,
        SUM(CASE WHEN dietary_flags->>'myplate_food_group' = 'other' THEN 1 ELSE 0 END) as myplate_other,
        SUM(CASE WHEN dietary_flags->'fda_nutritional_claims' ? 'low_sodium' THEN 1 ELSE 0 END) as low_sodium_count,
        SUM(CASE WHEN dietary_flags->'fda_nutritional_claims' ? 'low_fat' THEN 1 ELSE 0 END) as low_fat_count,
        SUM(CASE WHEN dietary_flags->'fda_nutritional_claims' ? 'high_fiber' THEN 1 ELSE 0 END) as high_fiber_count,
        SUM(CASE WHEN dietary_flags->'fda_nutritional_claims' ? 'high_protein' THEN 1 ELSE 0 END) as high_protein_count,
        SUM(CASE WHEN jsonb_array_length(dietary_flags->'potential_allergens') > 0 THEN 1 ELSE 0 END) as potential_allergens_detected
    INTO stats_record
    FROM food_items;
    
    RETURN QUERY SELECT 
        stats_record.updated_count,
        stats_record.myplate_vegetables,
        stats_record.myplate_fruits,
        stats_record.myplate_grains,
        stats_record.myplate_protein,
        stats_record.myplate_dairy,
        stats_record.myplate_other,
        stats_record.low_sodium_count,
        stats_record.low_fat_count,
        stats_record.high_fiber_count,
        stats_record.high_protein_count,
        stats_record.potential_allergens_detected;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- VALIDATION QUERIES
-- =============================================================================

-- Query to validate MyPlate mappings
CREATE OR REPLACE VIEW myplate_mapping_validation AS
SELECT 
    food_category,
    dietary_flags->>'myplate_food_group' as myplate_group,
    COUNT(*) as item_count
FROM food_items 
WHERE dietary_flags IS NOT NULL
GROUP BY food_category, dietary_flags->>'myplate_food_group'
ORDER BY item_count DESC;

-- Query to validate FDA nutritional claims
CREATE OR REPLACE VIEW fda_nutritional_claims_summary AS
SELECT 
    jsonb_array_elements_text(dietary_flags->'fda_nutritional_claims') as claim,
    COUNT(*) as claim_count
FROM food_items 
WHERE dietary_flags->'fda_nutritional_claims' IS NOT NULL
GROUP BY claim
ORDER BY claim_count DESC;

-- Query to validate allergen detection
CREATE OR REPLACE VIEW allergen_detection_summary AS
SELECT 
    jsonb_array_elements_text(dietary_flags->'potential_allergens') as allergen,
    COUNT(*) as detection_count
FROM food_items 
WHERE dietary_flags->'potential_allergens' IS NOT NULL 
    AND jsonb_array_length(dietary_flags->'potential_allergens') > 0
GROUP BY allergen
ORDER BY detection_count DESC;

-- =============================================================================
-- SAMPLE QUERIES FOR TESTING
-- =============================================================================

-- Test MyPlate food group mappings
-- SELECT food_category, map_to_myplate_group(food_category) FROM food_items WHERE food_category IS NOT NULL GROUP BY food_category ORDER BY food_category;

-- Test FDA nutritional flags  
-- SELECT description, calculate_fda_nutritional_flags(nutrients, serving_size) FROM food_items WHERE nutrients IS NOT NULL LIMIT 10;

-- Test allergen detection
-- SELECT description, detect_fda_allergens(ingredients, description) FROM food_items LIMIT 10;

-- Test complete dietary flags generation
-- SELECT description, generate_dietary_flags(food_category, nutrients, serving_size, ingredients, description) FROM food_items LIMIT 5;