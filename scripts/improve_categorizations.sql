-- Improve food group categorizations
-- Based on validation results, some categories need better MyPlate mapping

-- Mixed dishes with meat/poultry should be protein
UPDATE food_items 
SET dietary_flags = jsonb_set(
    dietary_flags, 
    '{myplate_food_group}', 
    '"protein"'
)
WHERE food_category IN (
    'Meat mixed dishes',
    'Poultry mixed dishes',
    'Beef mixed dishes', 
    'Pork mixed dishes',
    'Poultry Products',
    'Beef Products',
    'Pork Products',
    'Lamb, Veal, and Game Products'
);

-- Fish and shellfish mixed dishes should be protein
UPDATE food_items 
SET dietary_flags = jsonb_set(
    dietary_flags, 
    '{myplate_food_group}', 
    '"protein"'
)
WHERE food_category ILIKE '%fish%' 
   OR food_category ILIKE '%seafood%'
   OR food_category ILIKE '%shellfish%'
   OR food_category ILIKE '%finfish%';

-- Mixed dishes with rice/pasta should be grains (if primarily grain-based)
UPDATE food_items 
SET dietary_flags = jsonb_set(
    dietary_flags, 
    '{myplate_food_group}', 
    '"grains"'
)
WHERE food_category IN (
    'Pasta mixed dishes, excludes macaroni and cheese',
    'Rice mixed dishes'
);

-- Some specific fruits should be in fruits category
UPDATE food_items 
SET dietary_flags = jsonb_set(
    dietary_flags, 
    '{myplate_food_group}', 
    '"fruits"'
)
WHERE food_category ILIKE '%fruit%' AND food_category NOT IN (
    'Fruits and Fruit Juices'  -- already correctly categorized
);