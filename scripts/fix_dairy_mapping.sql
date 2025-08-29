-- Fix Dairy and Egg Products mapping
-- This should be classified as 'dairy' not 'protein'

UPDATE food_items 
SET dietary_flags = jsonb_set(
    dietary_flags, 
    '{myplate_food_group}', 
    '"dairy"'
)
WHERE food_category = 'Dairy and Egg Products';