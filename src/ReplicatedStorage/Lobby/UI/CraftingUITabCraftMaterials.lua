-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:53 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Lobby.UI.CraftingUITabBase)
local v_u_2 = require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_3 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_6 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_7 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_8 = require(game.ReplicatedStorage.Lobby.UI.MaterialsRequiredDisplay)
local v_u_9 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_10 = require(game.ReplicatedStorage.Lobby.UI.CraftingUISearchSection)
require(game.ReplicatedStorage.Shared.Dependency)
return {
    ["Tab"] = "CraftingUITabCraftMaterials",
    ["new"] = function(_, p_u_11, p_u_12, p_u_13) --[[ Name: new ]] --[[ Line: 22 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_4, (copy 3): v_u_8, (copy 4): v_u_5, (copy 5): v_u_3, (copy 6): v_u_2, (copy 7): v_u_10, (copy 8): v_u_6, (copy 9): v_u_7, (copy 10): v_u_9 ]]
        local v14 = v_u_1:new()
        local l__spui_0 = p_u_11._spui
        local l__menus_0 = p_u_11._menus
        local v_u_15 = nil
        local v_u_16 = nil
        local v_u_17 = nil
        local v_u_18 = nil
        local v_u_19 = nil
        local v_u_20 = v_u_4:new()
        local v_u_21 = 0
        local v_u_22 = -1
        local v_u_23 = 1
        local v_u_24 = nil
        v14.cons = function(p25) --[[ Name: cons ]] --[[ Line: 41 ]]
            --[[ Upvalues: (ref 1): v_u_15, (copy 2): p_u_13, (ref 3): v_u_16, (ref 4): v_u_17, (ref 5): v_u_18, (ref 6): v_u_19, (ref 7): v_u_24, (copy 8): v_u_20, (ref 9): v_u_8 ]]
            v_u_15 = p_u_13.PrimaryPart.SurfaceGui.Frame.SelectedInfoSection.CraftingUITabCraftMaterials
            v_u_16 = v_u_15.NameDisplay
            v_u_17 = v_u_15.DescriptionDisplay
            v_u_18 = v_u_15.IconFrame.Icon
            v_u_19 = v_u_15.OwnedDisplay
            v_u_24 = v_u_15.AmountDisplay
            v_u_20:push_back(v_u_8:new(v_u_15.RequirementDisplay1))
            v_u_20:push_back(v_u_8:new(v_u_15.RequirementDisplay2))
            v_u_20:push_back(v_u_8:new(v_u_15.RequirementDisplay3))
            v_u_20:push_back(v_u_8:new(v_u_15.RequirementDisplay4))
            p25:clear_selected_display()
        end;
        v14.clear_selected_display = function(p26) --[[ Name: clear_selected_display ]] --[[ Line: 57 ]]
            --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_17, (ref 3): v_u_18, (ref 4): v_u_5, (ref 5): v_u_19, (copy 6): v_u_20, (ref 7): v_u_22, (copy 8): p_u_12 ]]
            v_u_16.Text = ""
            v_u_17.Text = ""
            v_u_18.Image = v_u_5:transparent_assetid()
            v_u_19.Text = "-"
            p26:update_craft_amount(0)
            for v27 = 1, v_u_20:count() do
                v_u_20:get(v27):set_visible(false)
            end;
            v_u_22 = -1
            p_u_12:get_craft_button():set_enabled(false)
        end;
        v14.set_visible = function(_, p28) --[[ Name: set_visible ]] --[[ Line: 70 ]]
            --[[ Upvalues: (ref 1): v_u_15, (copy 2): p_u_12 ]]
            v_u_15.Visible = p28
            if p28 then
                p_u_12:get_craft_button():set_visible(true)
                p_u_12:get_craft_button():set_enabled(false)
                p_u_12:get_use_button():set_visible(false)
            end;
        end;
        v14.get_elements_list = function(_) --[[ Name: get_elements_list ]] --[[ Line: 79 ]]
            --[[ Upvalues: (copy 1): p_u_11, (ref 2): v_u_4, (ref 3): v_u_3, (ref 4): v_u_2, (copy 5): p_u_12, (ref 6): v_u_10 ]]
            local v29 = p_u_11._player_blob_manager:get_player_blob()
            local v30 = v_u_4:new()
            for v31, v32 in v_u_3:singleton():material_recipe_key_itr() do
                local v33, v34 = v32:has_display_requirement_materialid()
                if v33 == true then
                    if v_u_2:get_count_of_material(v29, v34) > 0 then
                        v30:push_back(v31)
                    end;
                else
                    v30:push_back(v31)
                end;
            end;
            local v35 = v_u_4:new()
            local v36 = v_u_4:new()
            local v37 = v_u_4:new()
            for v38 = 1, v30:count() do
                local v39 = v30:get(v38)
                if v_u_2:can_craft_requirements_dict(v29, v_u_3:singleton():get_material_recipe_requirements_dict(v39)) then
                    v36:push_back(v39)
                else
                    v37:push_back(v39)
                end;
            end;
            local function f_sort_filter_recipe_id_list(p40) --[[ Name: sort_filter_recipe_id_list ]] --[[ Line: 112 ]]
                --[[ Upvalues: (ref 1): p_u_12, (ref 2): v_u_3, (ref 3): v_u_10 ]]
                local v_u_41 = string.lower(p_u_12:get_search_name())
                p40:remove_if(function(p42, _) --[[ Line: 114 ]]
                    --[[ Upvalues: (ref 1): v_u_3, (copy 2): v_u_41 ]]
                    return string.find(string.lower((v_u_3:singleton():get_material_recipe_name(p42))), v_u_41, 1, true) == nil;
                end)
                if p_u_12:get_sort_type() == v_u_10.SortType.Category1 then
                    local function f_material_type_sort(p43, p44) --[[ Name: material_type_sort ]] --[[ Line: 119 ]]
                        --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_3 ]]
                        return v_u_10:materialid_get_type_sort_value(v_u_3:singleton():get_material_recipe_material_id(p44)) > v_u_10:materialid_get_type_sort_value(v_u_3:singleton():get_material_recipe_material_id(p43)) == false and -1 or 1;
                    end;
                    local function f_material_type_sort_inverse(p45, p46) --[[ Name: material_type_sort_inverse ]] --[[ Line: 131 ]]
                        --[[ Upvalues: (copy 1): f_material_type_sort ]]
                        return f_material_type_sort(p45, p46) * -1;
                    end;
                    if p_u_12:get_sort_order() == v_u_10.SortOrder.Ascending then
                        p40:sort(f_material_type_sort)
                    else
                        p40:sort(f_material_type_sort_inverse)
                    end;
                else
                    if p_u_12:get_sort_type() == v_u_10.SortType.Category2 then
                        local function f_material_name_sort(p47, p48) --[[ Name: material_name_sort ]] --[[ Line: 141 ]]
                            --[[ Upvalues: (ref 1): v_u_3 ]]
                            return v_u_3:singleton():get_material_recipe_name(p48) > v_u_3:singleton():get_material_recipe_name(p47) == false and -1 or 1;
                        end;
                        local function f_material_name_sort_inverse(p49, p50) --[[ Name: material_name_sort_inverse ]] --[[ Line: 146 ]]
                            --[[ Upvalues: (ref 1): v_u_3 ]]
                            return (v_u_3:singleton():get_material_recipe_name(p50) > v_u_3:singleton():get_material_recipe_name(p49) == false and -1 or 1) * -1;
                        end;
                        if p_u_12:get_sort_order() == v_u_10.SortOrder.Ascending then
                            p40:sort(f_material_name_sort)
                            return;
                        end;
                        p40:sort(f_material_name_sort_inverse)
                    end;
                    return;
                end;
            end;
            f_sort_filter_recipe_id_list(v36)
            f_sort_filter_recipe_id_list(v37)
            v35:push_back_from_list(v36)
            v35:push_back_from_list(v37)
            return v35;
        end;
        v14.get_empty_text = function(_) --[[ Name: get_empty_text ]] --[[ Line: 167 ]]
            return "No available material crafting recipes. Craftable materials will show up here when you own any of the prerequisite materials.";
        end;
        v14.redraw_list = function(p51) --[[ Name: redraw_list ]] --[[ Line: 171 ]]
            --[[ Upvalues: (copy 1): p_u_12, (copy 2): p_u_11, (ref 3): v_u_21, (ref 4): v_u_3, (ref 5): v_u_2 ]]
            p_u_12:clear_list()
            local v52 = p_u_11._player_blob_manager:get_player_blob()
            local v53 = p51:get_elements_list()
            if v53:count() == 0 then
                p_u_12:set_empty_display_visible(true)
            end;
            local v54 = p_u_12:get_list_elements()
            for v55 = 1, v54:count() do
                local v56 = v54:get(v55)
                local v57 = v_u_21 * v54:count() + v55
                if v57 <= v53:count() then
                    local v58 = v53:get(v57)
                    local v59 = v_u_3:singleton():get_material_recipe_requirements_dict(v58)
                    v56:set_visible(true)
                    v56:set_info(v58, v_u_3:singleton():get_material_recipe_icon(v58), v_u_2:get_count_of_material(v52, v_u_3:singleton():get_material_recipe_material_id(v58)))
                    if v_u_2:can_craft_requirements_dict(v52, v59) then
                        v56:set_alpha(1)
                    else
                        v56:set_alpha(0.35)
                    end;
                end;
            end;
        end;
        v14.page_up = function(p60) --[[ Name: page_up ]] --[[ Line: 206 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            v_u_21 = v_u_21 - 1
            p60:redraw_list()
        end;
        v14.page_down = function(p61) --[[ Name: page_down ]] --[[ Line: 211 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            v_u_21 = v_u_21 + 1
            p61:redraw_list()
        end;
        v14.can_page_up = function(_) --[[ Name: can_page_up ]] --[[ Line: 216 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            return v_u_21 > 0;
        end;
        v14.reset_page = function(_) --[[ Name: reset_page ]] --[[ Line: 220 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            v_u_21 = 0
        end;
        v14.can_page_down = function(p62) --[[ Name: can_page_down ]] --[[ Line: 222 ]]
            --[[ Upvalues: (ref 1): v_u_21, (copy 2): p_u_12 ]]
            return (v_u_21 + 1) * p_u_12:get_list_elements():count() < p62:get_elements_list():count();
        end;
        local function f_update_selected_material_display() --[[ Name: update_selected_material_display ]] --[[ Line: 226 ]]
            --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_22, (ref 3): v_u_6, (copy 4): p_u_11, (ref 5): v_u_16, (ref 6): v_u_18, (ref 7): v_u_19, (ref 8): v_u_2, (ref 9): v_u_17, (copy 10): v_u_20, (ref 11): v_u_23, (copy 12): p_u_12 ]]
            if v_u_3:singleton():get_material_recipe(v_u_22) == nil then
                v_u_6:errf("CraftingUITabCraftMaterials list_element_pressed invalid id(%s)", (tostring(v_u_22)))
            end;
            local v63 = p_u_11._player_blob_manager:get_player_blob()
            v_u_16.Text = v_u_3:singleton():get_material_recipe_name(v_u_22)
            v_u_18.Image = v_u_3:singleton():get_material_recipe_icon(v_u_22)
            v_u_19.Text = v_u_2:get_count_of_material(v63, v_u_3:singleton():get_material_recipe_material_id(v_u_22))
            local v64 = v_u_3:singleton():get_material(v_u_3:singleton():get_material_recipe_material_id(v_u_22))
            v_u_16.TextColor3 = v_u_3:singleton():tier_get_color(v64:get_tier())
            v_u_17.Text = v64:get_description()
            for v65 = 1, v_u_20:count() do
                v_u_20:get(v65):set_visible(false)
            end;
            local v66 = v_u_3:singleton():get_material_recipe_requirements_dict(v_u_22, v_u_23)
            local v67 = v66:key_list()
            for v68 = 1, v_u_20:count() do
                if v67:count() < v68 then
                    break;
                end;
                local v69 = v67:get(v68)
                local v70 = v_u_20:get(v68)
                v70:set_visible(true)
                v70:set_info(v_u_3:singleton():get_material_name(v69), v_u_3:singleton():get_material_icon(v69), v_u_3:singleton():tier_get_color(v_u_3:singleton():get_material_tier(v69)), v_u_2:get_count_of_material(v63, v69), v66:get(v69))
            end;
            p_u_12:get_craft_button():set_enabled((v_u_2:can_craft_requirements_dict(v63, v66)))
        end;
        v14.list_element_pressed = function(p71, _, p72) --[[ Name: list_element_pressed ]] --[[ Line: 267 ]]
            --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_6, (ref 3): v_u_22, (copy 4): p_u_11, (ref 5): v_u_23, (ref 6): v_u_2, (copy 7): f_update_selected_material_display ]]
            if v_u_3:singleton():get_material_recipe(p72) == nil then
                v_u_6:errf("CraftingUITabCraftMaterials list_element_pressed invalid id(%s)", (tostring(p72)))
            end;
            v_u_22 = p72
            if v_u_2:can_craft_requirements_dict(p_u_11._player_blob_manager:get_player_blob(), (v_u_3:singleton():get_material_recipe_requirements_dict(v_u_22, v_u_23))) then
                p71:update_craft_amount(1)
            else
                p71:update_craft_amount(0)
            end;
            f_update_selected_material_display()
        end;
        v14.craft_pressed = function(p_u_73) --[[ Name: craft_pressed ]] --[[ Line: 282 ]]
            --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_22, (copy 3): l__menus_0, (ref 4): v_u_7, (copy 5): p_u_11, (copy 6): l__spui_0, (ref 7): v_u_9, (ref 8): v_u_23, (copy 9): p_u_12 ]]
            if v_u_3:singleton():get_material_recipe(v_u_22) == nil then
                return l__menus_0:push_menu(v_u_7:new(p_u_11, l__spui_0, l__menus_0):set_text("Failed", "No material selected"));
            end;
            p_u_11._sfx_manager:play_sfx(v_u_9.SFX_BUTTONPRESS)
            local v_u_74 = l__menus_0:push_menu(v_u_7:new(p_u_11, l__spui_0, l__menus_0):set_text("Crafting...", ""):set_close_button_visible(false))
            p_u_11._shop_local_protocol:try_craft_material_recipe(v_u_22, v_u_23, function(p75, p_u_76, p77) --[[ Line: 289 ]]
                --[[ Upvalues: (ref 1): l__menus_0, (copy 2): v_u_74, (ref 3): v_u_7, (ref 4): p_u_11, (ref 5): l__spui_0, (ref 6): v_u_22, (copy 7): p_u_73, (ref 8): v_u_9, (ref 9): p_u_12, (ref 10): v_u_3 ]]
                if p75 == true then
                    p_u_11._player_blob_manager:do_sync(function(_) --[[ Line: 296 ]]
                        --[[ Upvalues: (ref 1): v_u_22, (ref 2): p_u_73, (ref 3): p_u_11, (ref 4): v_u_9, (ref 5): p_u_12, (ref 6): l__menus_0, (ref 7): v_u_74, (ref 8): v_u_7, (ref 9): l__spui_0, (ref 10): v_u_3, (copy 11): p_u_76 ]]
                        local v78 = v_u_22
                        p_u_73:clear_selected_display()
                        p_u_73:redraw_list()
                        p_u_11._sfx_manager:play_sfx(v_u_9.SFX_ACQUIRE)
                        p_u_12:set_on_refocus_selected_element(v78)
                        l__menus_0:remove_menu(v_u_74)
                        l__menus_0:push_menu(v_u_7:new(p_u_11, l__spui_0, l__menus_0):set_text("Crafted!", string.format("You crafted %s x%d!", v_u_3:singleton():get_material_name(v_u_3:singleton():get_material_recipe_material_id(v78)), v_u_3:singleton():get_material_recipe_result_count(v78) * p_u_76)))
                    end)
                else
                    l__menus_0:remove_menu(v_u_74)
                    l__menus_0:push_menu(v_u_7:new(p_u_11, l__spui_0, l__menus_0):set_text("Crafting failed.", p77))
                end;
            end)
        end;
        v14.update_craft_amount = function(_, p79) --[[ Name: update_craft_amount ]] --[[ Line: 317 ]]
            --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_24 ]]
            v_u_23 = p79
            if v_u_23 <= 0 then
                v_u_24.Text = "-"
            else
                v_u_24.Text = tostring(v_u_23)
            end;
        end;
        v14.show_craft_amount_buttons = function(_) --[[ Name: show_craft_amount_buttons ]] --[[ Line: 326 ]]
            --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_23, (copy 3): p_u_11, (ref 4): v_u_3, (ref 5): v_u_2 ]]
            if v_u_22 == -1 then
                return false, false;
            else
                return v_u_23 > 1, v_u_2:can_craft_requirements_dict(p_u_11._player_blob_manager:get_player_blob(), (v_u_3:singleton():get_material_recipe_requirements_dict(v_u_22, v_u_23 + 1)));
            end;
        end;
        v14.craft_amount_button_pressed = function(p80, p81) --[[ Name: craft_amount_button_pressed ]] --[[ Line: 334 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_23, (copy 3): f_update_selected_material_display ]]
            p80:update_craft_amount(v_u_5:clamp(v_u_23 + p81, 1, v_u_5:input_max_number()))
            f_update_selected_material_display()
        end;
        v14.select_element = function(p82, p83) --[[ Name: select_element ]] --[[ Line: 339 ]]
            --[[ Upvalues: (copy 1): p_u_12, (ref 2): v_u_6, (ref 3): v_u_21 ]]
            local v84 = p82:get_elements_list()
            local v85 = p_u_12:get_list_elements()
            local v88 = v84:find(p83, function(p86, p87) --[[ Line: 343 ]]
                return p86 == p87;
            end)
            if v88 == -1 then
                return v_u_6:warnf("CraftingUITabCraftMaterials:select_element can\'t find(%s)", (tostring(p83)));
            end;
            v_u_21 = math.floor((v88 - 1) / v85:count())
            p_u_12:update_current_tab()
            local v89 = v88 - v_u_21 * v85:count()
            if v89 <= 0 or v85:count() < v89 then
                return v_u_6:warnf("CraftingUITabCraftMaterials:select_element invalid select_element_index(%s)", (tostring(v89)));
            end;
            local v90 = v85:get(v89)
            p_u_12:list_element_pressed(v90, v89, v90:get_data())
        end;
        v14.is_search_section_enabled = function(_) --[[ Name: is_search_section_enabled ]] --[[ Line: 366 ]]
            return true;
        end;
        v14.get_category_names = function(_) --[[ Name: get_category_names ]] --[[ Line: 367 ]]
            return "Type", "Name";
        end;
        v14:cons()
        return v14;
    end
};
