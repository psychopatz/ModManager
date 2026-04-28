-- DT_MANUAL_EDITOR_BEGIN
-- {
--   "manual_id": "dt_update_2026_03_27",
--   "module": "common",
--   "title": "March 27, 2026 Update",
--   "description": "Generated liquid registry and liter-based pricing",
--   "start_page_id": "update_overview",
--   "audiences": [
--     "common"
--   ],
--   "sort_order": 10,
--   "release_version": "2026-03-27",
--   "popup_version": "2026-03-27",
--   "auto_open_on_update": true,
--   "is_whats_new": true,
--   "manual_type": "whats_new",
--   "show_in_library": false,
--   "support_url": "",
--   "banner_title": "",
--   "banner_text": "",
--   "banner_action_label": "",
--   "source_folder": "WhatsNew",
--   "chapters": [
--     {
--       "id": "release_notes",
--       "title": "Release Notes",
--       "description": "What changed in this update."
--     }
--   ],
--   "pages": [
--     {
--       "id": "update_overview",
--       "chapter_id": "release_notes",
--       "title": "Liquid Registry And Pricing",
--       "keywords": [
--         "update",
--         "release",
--         "patch",
--         "what's new"
--       ],
--       "blocks": [
--         {
--           "type": "heading",
--           "id": "manual-library-upgrade",
--           "level": 1,
--           "text": "Liquid Registry And Pricing"
--         },
--         {
--           "type": "bullet_list",
--           "items": [
--             "The Dynamic Trading Manager now rebuilds DT_Liquid.lua automatically from vanilla FluidContainer scripts during normal add and update runs.",
--             "A generated DT_Fluids.lua registry now tracks fluid tags and basePricePerLiter values for named liquids like water, petrol, bleach, alcohol, juice, and milk.",
--             "Filled containers are now priced as empty container value plus liquid liters, so gasoline in a bottle follows gasoline pricing instead of bottle pricing.",
--             "Filled liquid items now use Fluid.* trade tags and category headers, while empty containers stay under their normal container category."
--           ]
--         },
--         {
--           "type": "callout",
--           "tone": "info",
--           "title": "How It Works",
--           "text": "Regenerate items through the Dynamic Trading Manager and the liquid container registry plus the fluid price registry will be rebuilt together from vanilla data."
--         }
--       ]
--     }
--   ]
-- }
-- DT_MANUAL_EDITOR_END
if DynamicTrading and DynamicTrading.RegisterManual then
    DynamicTrading.RegisterManual("dt_update_2026_03_27", {
        title = "March 27, 2026 Update",
        description = "Generated liquid registry and liter-based pricing",
        startPageId = "update_overview",
        audiences = { "common" },
        sortOrder = 10,
        releaseVersion = "2026-03-27",
        popupVersion = "2026-03-27",
        autoOpenOnUpdate = true,
        isWhatsNew = true,
        manualType = "whats_new",
        showInLibrary = false,
        supportUrl = "",
        bannerTitle = "",
        bannerText = "",
        bannerActionLabel = "",
        chapters = {
            {
                id = "release_notes",
                title = "Release Notes",
                description = "What changed in this update.",
            },
        },
        pages = {
            {
                id = "update_overview",
                chapterId = "release_notes",
                title = "Liquid Registry And Pricing",
                keywords = { "update", "release", "patch", "what's new" },
                blocks = {
                    { type = "heading", id = "manual-library-upgrade", level = 1, text = "Liquid Registry And Pricing" },
                    { type = "bullet_list", items = { "The Dynamic Trading Manager now rebuilds DT_Liquid.lua automatically from vanilla FluidContainer scripts during normal add and update runs.", "A generated DT_Fluids.lua registry now tracks fluid tags and basePricePerLiter values for named liquids like water, petrol, bleach, alcohol, juice, and milk.", "Filled containers are now priced as empty container value plus liquid liters, so gasoline in a bottle follows gasoline pricing instead of bottle pricing.", "Filled liquid items now use Fluid.* trade tags and category headers, while empty containers stay under their normal container category." } },
                    { type = "callout", tone = "info", title = "How It Works", text = "Regenerate items through the Dynamic Trading Manager and the liquid container registry plus the fluid price registry will be rebuilt together from vanilla data." },
                },
            },
        },
    })
end
