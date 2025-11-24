-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:52 PM
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
local v_u_8 = require(game.ReplicatedStorage.Avatar.EquipmentUpgradeDatabase)
local v_u_9 = require(game.ReplicatedStorage.Lobby.UI.MaterialsRequiredDisplay)
local v_u_10 = require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_11 = require(game.ReplicatedStorage.Avatar.GearStatsDescriptions)
local v_u_12 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentDatabase)
local v_u_13 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_14 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_15 = require(game.ReplicatedStorage.Lobby.UI.GearEquipV2UI.GearEquipV2GearStatDisplay)
local v_u_16 = require(game.ReplicatedStorage.Lobby.Menus.GearSelectUI)
local v_u_17 = require(game.ReplicatedStorage.Lobby.Menus.UpgradeBoostUI)
local v_u_18 = require(game.ReplicatedStorage.Lobby.UI.CraftingUISearchSection)
return {
    ["Tab"] = "CraftingUITabGearUpgrades",
    ["new"] = function(_, p_u_19, p_u_20, p_u_21) --[[ Name: new ]] --[[ Line: 27 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_4, (copy 3): v_u_9, (copy 4): v_u_6, (copy 5): v_u_8, (copy 6): v_u_2, (copy 7): v_u_18, (copy 8): v_u_10, (copy 9): v_u_15, (copy 10): v_u_11, (copy 11): v_u_3, (copy 12): v_u_7, (copy 13): v_u_14, (copy 14): v_u_16, (copy 15): v_u_17, (copy 16): v_u_5, (copy 17): v_u_13, (copy 18): v_u_12 ]]
        local v22 = v_u_1:new()
        local l__spui_0 = p_u_19._spui
        local l__menus_0 = p_u_19._menus
        local v_u_23 = nil
        local v_u_24 = nil
        local v_u_25 = v_u_4:new()
        local v_u_26 = v_u_4:new()
        local v_u_27 = v_u_4:new()
        local v_u_28 = 0
        local v_u_29 = -1
        v22.cons = function(p30) --[[ Name: cons ]] --[[ Line: 43 ]]
            --[[ Upvalues: (ref 1): v_u_23, (copy 2): p_u_21, (ref 3): v_u_24, (copy 4): v_u_25, (ref 5): v_u_9, (copy 6): v_u_26, (copy 7): v_u_27 ]]
            v_u_23 = p_u_21.PrimaryPart.SurfaceGui.Frame.SelectedInfoSection.CraftingUITabGearUpgrades
            v_u_24 = v_u_23.NameDisplay
            v_u_25:push_back(v_u_9:new(v_u_23.RequirementDisplay1))
            v_u_25:push_back(v_u_9:new(v_u_23.RequirementDisplay2))
            v_u_25:push_back(v_u_9:new(v_u_23.RequirementDisplay3))
            v_u_25:push_back(v_u_9:new(v_u_23.RequirementDisplay4))
            v_u_26:push_back_table_list({
                v_u_23.StatDisplay1,
                v_u_23.StatDisplay2,
                v_u_23.StatDisplay3,
                v_u_23.StatDisplay4
            })
            v_u_27:push_back_table_list({
                v_u_23.StatDescription1,
                v_u_23.StatDescription2,
                v_u_23.StatDescription3,
                v_u_23.StatDescription4
            })
            p30:clear_selected_display()
        end;
        v22.select_element = function(p31, p32) --[[ Name: select_element ]] --[[ Line: 69 ]]
            --[[ Upvalues: (copy 1): p_u_20, (ref 2): v_u_6, (ref 3): v_u_28 ]]
            local v33 = p31:get_elements_list()
            local v34 = p_u_20:get_list_elements()
            local v35 = v33:find(p32)
            if v35 == -1 then
                return v_u_6:warnf("CraftingUITabGearUpgrades:select_element can\'t find(%s)", (tostring(p32)));
            end;
            v_u_28 = math.floor((v35 - 1) / v34:count())
            p_u_20:update_current_tab()
            local v36 = v35 - v_u_28 * v34:count()
            if v36 <= 0 or v34:count() < v36 then
                return v_u_6:warnf("CraftingUITabGearUpgrades:select_element invalid select_element_index(%s)", (tostring(v36)));
            end;
            local v37 = v34:get(v36)
            p_u_20:list_element_pressed(v37, v36, v37:get_data())
        end;
        v22.clear_selected_display = function(_) --[[ Name: clear_selected_display ]] --[[ Line: 94 ]]
            --[[ Upvalues: (ref 1): v_u_24, (copy 2): v_u_26, (copy 3): v_u_27, (copy 4): v_u_25, (ref 5): v_u_29, (copy 6): p_u_20 ]]
            v_u_24.Text = ""
            for v38 = 1, v_u_26:count() do
                v_u_26:get(v38).Visible = false
                v_u_27:get(v38).Visible = false
            end;
            for v39 = 1, v_u_25:count() do
                v_u_25:get(v39):set_visible(false)
            end;
            v_u_29 = -1
            p_u_20:get_craft_button():set_enabled(false)
        end;
        v22.set_visible = function(_, p40) --[[ Name: set_visible ]] --[[ Line: 107 ]]
            --[[ Upvalues: (ref 1): v_u_23, (copy 2): p_u_20 ]]
            v_u_23.Visible = p40
            if p40 then
                p_u_20:get_craft_button():set_visible(true)
                p_u_20:get_craft_button():set_enabled(false)
                p_u_20:get_use_button():set_visible(false)
            end;
        end;
        v22.get_elements_list = function(_) --[[ Name: get_elements_list ]] --[[ Line: 116 ]]
            --[[ Upvalues: (copy 1): p_u_19, (ref 2): v_u_4, (ref 3): v_u_8, (ref 4): v_u_2, (copy 5): p_u_20, (ref 6): v_u_18 ]]
            local v_u_41 = p_u_19._player_blob_manager:get_player_blob()
            local v42 = v_u_4:new()
            local v43 = v_u_8:singleton():equipment_upgrade_id_list()
            local v44 = v_u_4:new()
            local v45 = v_u_4:new()
            for v46 = 1, v43:count() do
                local v47 = v43:get(v46)
                if v_u_2:can_craft_requirements_dict(v_u_41, (v_u_8:singleton():get_requirements_dict_for_id(v47))) then
                    v44:push_front(v47)
                else
                    v45:push_back(v47)
                end;
            end;
            local function f_sort_filter_recipe_id_list(p48) --[[ Name: sort_filter_recipe_id_list ]] --[[ Line: 134 ]]
                --[[ Upvalues: (ref 1): p_u_20, (ref 2): v_u_8, (ref 3): v_u_18, (ref 4): v_u_2, (copy 5): v_u_41 ]]
                local v_u_49 = string.lower(p_u_20:get_search_name())
                p48:remove_if(function(p50, _) --[[ Line: 136 ]]
                    --[[ Upvalues: (ref 1): v_u_8, (copy 2): v_u_49 ]]
                    return string.find(string.lower(v_u_8:singleton():get_equipment_upgrade_for_id(p50):get_name()), v_u_49, 1, true) == nil;
                end)
                if p_u_20:get_sort_type() == v_u_18.SortType.Category1 then
                    local function f_recipe_name_sort(p51, p52) --[[ Name: recipe_name_sort ]] --[[ Line: 141 ]]
                        --[[ Upvalues: (ref 1): v_u_8 ]]
                        return v_u_8:singleton():get_equipment_upgrade_for_id(p52):get_name() > v_u_8:singleton():get_equipment_upgrade_for_id(p51):get_name() == false and -1 or 1;
                    end;
                    local function f_recipe_name_sort_inverse(p53, p54) --[[ Name: recipe_name_sort_inverse ]] --[[ Line: 148 ]]
                        --[[ Upvalues: (copy 1): f_recipe_name_sort ]]
                        return f_recipe_name_sort(p53, p54) * -1;
                    end;
                    if p_u_20:get_sort_order() == v_u_18.SortOrder.Ascending then
                        p48:sort(f_recipe_name_sort)
                    else
                        p48:sort(f_recipe_name_sort_inverse)
                    end;
                else
                    if p_u_20:get_sort_type() == v_u_18.SortType.Category2 then
                        local function f_craft_count_sort(p55, p56) --[[ Name: craft_count_sort ]] --[[ Line: 158 ]]
                            --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_2, (ref 3): v_u_41 ]]
                            return v_u_2:can_craft_count_of_requirements_dict(v_u_41, (v_u_8:singleton():get_requirements_dict_for_id(p56))) - v_u_2:can_craft_count_of_requirements_dict(v_u_41, (v_u_8:singleton():get_requirements_dict_for_id(p55)));
                        end;
                        local function f_craft_count_sort_inverse(p57, p58) --[[ Name: craft_count_sort_inverse ]] --[[ Line: 163 ]]
                            --[[ Upvalues: (copy 1): f_craft_count_sort ]]
                            return f_craft_count_sort(p57, p58) * -1;
                        end;
                        if p_u_20:get_sort_order() == v_u_18.SortOrder.Ascending then
                            p48:sort(f_craft_count_sort)
                            return;
                        end;
                        p48:sort(f_craft_count_sort_inverse)
                    end;
                    return;
                end;
            end;
            f_sort_filter_recipe_id_list(v44)
            f_sort_filter_recipe_id_list(v45)
            v42:push_back_from_list(v44)
            v42:push_back_from_list(v45)
            return v42;
        end;
        v22.redraw_list = function(p59) --[[ Name: redraw_list ]] --[[ Line: 183 ]]
            --[[ Upvalues: (copy 1): p_u_20, (copy 2): p_u_19, (ref 3): v_u_28, (ref 4): v_u_8, (ref 5): v_u_2 ]]
            p_u_20:clear_list()
            local v60 = p_u_19._player_blob_manager:get_player_blob()
            local v61 = p59:get_elements_list()
            local v62 = p_u_20:get_list_elements()
            for v63 = 1, v62:count() do
                local v64 = v62:get(v63)
                local v65 = v_u_28 * v62:count() + v63
                if v65 <= v61:count() then
                    local v66 = v61:get(v65)
                    local v67 = v_u_8:singleton():get_requirements_dict_for_id(v66)
                    local v68 = v_u_8:singleton():get_equipment_upgrade_for_id(v66)
                    v64:set_visible(true)
                    v64:set_info(v66, v68:get_icon(), v_u_2:can_craft_count_of_requirements_dict(v60, v67))
                    if v_u_2:can_craft_requirements_dict(v60, v67) then
                        v64:set_alpha(1)
                    else
                        v64:set_alpha(0.35)
                    end;
                end;
            end;
        end;
        v22.page_up = function(p69) --[[ Name: page_up ]] --[[ Line: 215 ]]
            --[[ Upvalues: (ref 1): v_u_28 ]]
            v_u_28 = v_u_28 - 1
            p69:redraw_list()
        end;
        v22.page_down = function(p70) --[[ Name: page_down ]] --[[ Line: 220 ]]
            --[[ Upvalues: (ref 1): v_u_28 ]]
            v_u_28 = v_u_28 + 1
            p70:redraw_list()
        end;
        v22.can_page_up = function(_) --[[ Name: can_page_up ]] --[[ Line: 225 ]]
            --[[ Upvalues: (ref 1): v_u_28 ]]
            return v_u_28 > 0;
        end;
        v22.reset_page = function(_) --[[ Name: reset_page ]] --[[ Line: 229 ]]
            --[[ Upvalues: (ref 1): v_u_28 ]]
            v_u_28 = 0
        end;
        v22.can_page_down = function(p71) --[[ Name: can_page_down ]] --[[ Line: 231 ]]
            --[[ Upvalues: (ref 1): v_u_28, (copy 2): p_u_20 ]]
            return (v_u_28 + 1) * p_u_20:get_list_elements():count() < p71:get_elements_list():count();
        end;
        v22.list_element_pressed = function(_, _, p72) --[[ Name: list_element_pressed ]] --[[ Line: 235 ]]
            --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_6, (ref 3): v_u_29, (copy 4): p_u_19, (ref 5): v_u_24, (ref 6): v_u_10, (copy 7): v_u_26, (copy 8): v_u_27, (ref 9): v_u_15, (ref 10): v_u_11, (copy 11): v_u_25, (ref 12): v_u_3, (ref 13): v_u_2, (copy 14): p_u_20 ]]
            if v_u_8:singleton():get_equipment_upgrade_for_id(p72) == nil then
                v_u_6:errf("CraftingUITabGearUpgrades list_element_pressed invalid upgradeid(%s)", (tostring(p72)))
            end;
            v_u_29 = p72
            local v73 = p_u_19._player_blob_manager:get_player_blob()
            local v74 = v_u_8:singleton():get_equipment_upgrade_for_id(p72)
            v_u_24.Text = v74:get_name()
            local v75 = v_u_10:get_top_stats(v74:get_gear_statmodifierobj())
            for v76 = 1, v_u_26:count() do
                local v77 = v_u_26:get(v76)
                local v78 = v_u_27:get(v76)
                if v75:count() < v76 then
                    v77.Visible = false
                    v78.Visible = false
                else
                    local l_Stat_0 = v75:get(v76).Stat
                    local l_Value_0 = v75:get(v76).Value
                    v77.Visible = true
                    v78.Visible = true
                    v77.Text = string.format("%s%d %s", l_Value_0 < 0 and "-" or "+", math.abs(l_Value_0), (v_u_10:type_to_name(l_Stat_0)))
                    v77.TextColor3 = v_u_10:gear_attrvalue_opts_get_color(l_Value_0, l_Stat_0, false)
                    v_u_15:display_stat_icon_for_sub_text(v77, l_Stat_0, 4)
                    v78.Text = v_u_11:get_description_for_stat(l_Stat_0)
                end;
            end;
            for v79 = 1, v_u_25:count() do
                v_u_25:get(v79):set_visible(false)
            end;
            local v80 = v_u_8:singleton():get_requirements_dict_for_id(v_u_29)
            local v81 = v80:key_list()
            for v82 = 1, v_u_25:count() do
                if v81:count() < v82 then
                    break;
                end;
                local v83 = v81:get(v82)
                local v84 = v_u_25:get(v82)
                v84:set_visible(true)
                v84:set_info(v_u_3:singleton():get_material_name(v83), v_u_3:singleton():get_material_icon(v83), v_u_3:singleton():tier_get_color(v_u_3:singleton():get_material_tier(v83)), v_u_2:get_count_of_material(v73, v83), v80:get(v83))
            end;
            p_u_20:get_craft_button():set_enabled(v_u_2:can_craft_requirements_dict(v73, (v_u_8:singleton():get_requirements_dict_for_id(v_u_29))))
        end;
        v22.craft_pressed = function(p_u_85) --[[ Name: craft_pressed ]] --[[ Line: 297 ]]
            --[[ Upvalues: (ref 1): v_u_29, (copy 2): l__menus_0, (ref 3): v_u_7, (copy 4): p_u_19, (copy 5): l__spui_0, (ref 6): v_u_14, (copy 7): p_u_20, (ref 8): v_u_16, (ref 9): v_u_17, (ref 10): v_u_5, (ref 11): v_u_6, (ref 12): v_u_13, (ref 13): v_u_8, (ref 14): v_u_12 ]]
            if v_u_29 < 0 then
                return l__menus_0:push_menu(v_u_7:new(p_u_19, l__spui_0, l__menus_0):set_text("Failed", "No upgrade selected"));
            end;
            p_u_19._sfx_manager:play_sfx(v_u_14.SFX_BUTTONPRESS)
            local v_u_86 = v_u_29
            p_u_20:set_on_refocus_selected_element(v_u_29)
            l__menus_0:push_menu(v_u_16:new(p_u_19, l__spui_0, l__menus_0, function(_, p_u_87) --[[ Line: 309 ]]
                --[[ Upvalues: (ref 1): l__menus_0, (ref 2): v_u_7, (ref 3): p_u_19, (ref 4): l__spui_0, (copy 5): v_u_86, (ref 6): v_u_17, (copy 7): p_u_85, (ref 8): v_u_5, (ref 9): v_u_6, (ref 10): v_u_13, (ref 11): v_u_8, (ref 12): v_u_12, (ref 13): v_u_14 ]]
                local v_u_88 = l__menus_0:push_menu(v_u_7:new(p_u_19, l__spui_0, l__menus_0):set_text("Upgrading...", ""):set_close_button_visible(false))
                p_u_19._shop_local_protocol:try_craft_gear_upgrade(v_u_86, p_u_87, function(p_u_89, p_u_90, p91) --[[ Line: 311 ]]
                    --[[ Upvalues: (ref 1): l__menus_0, (ref 2): v_u_17, (ref 3): p_u_19, (ref 4): l__spui_0, (copy 5): p_u_87, (ref 6): v_u_86, (ref 7): p_u_85, (copy 8): v_u_88, (ref 9): v_u_7, (ref 10): v_u_5, (ref 11): v_u_6, (ref 12): v_u_13, (ref 13): v_u_8, (ref 14): v_u_12, (ref 15): v_u_14 ]]
                    if p91 == true then
                        l__menus_0:push_menu(v_u_17:new(p_u_19, l__spui_0, l__menus_0, p_u_87, v_u_86, function() --[[ Line: 319 ]]
                            --[[ Upvalues: (ref 1): p_u_85 ]]
                            p_u_85:clear_selected_display()
                            p_u_85:redraw_list()
                        end))
                        l__menus_0:remove_menu(v_u_88)
                        return;
                    elseif p_u_89 == true then
                        p_u_19._player_blob_manager:do_sync(function(p92) --[[ Line: 342 ]]
                            --[[ Upvalues: (ref 1): p_u_85, (ref 2): v_u_13, (ref 3): p_u_87, (ref 4): l__menus_0, (ref 5): v_u_88, (ref 6): v_u_8, (ref 7): v_u_86, (ref 8): v_u_12, (ref 9): p_u_19, (ref 10): v_u_14, (ref 11): v_u_7, (ref 12): l__spui_0 ]]
                            p_u_85:clear_selected_display()
                            p_u_85:redraw_list()
                            local v93 = v_u_13:playerblob_ownedid_to_equipmentid(p92, p_u_87)
                            l__menus_0:remove_menu(v_u_88)
                            local v94 = v_u_13:get_ownedid_upgrade_count(p92, p_u_87)
                            local v95 = tostring(v_u_8:singleton():get_equipment_upgrade_for_id(v_u_86):get_name())
                            local v96 = tostring(v_u_12:singleton():get_equipment_for_id(v93):get_name())
                            local v97
                            if v94 <= 1 then
                                v97 = string.format("Added upgrade \"%s\" to \"%s\".", v95, v96)
                            else
                                v97 = string.format("Added upgrade \"%s\" to \"%s +%d\".", v95, v96, tonumber(v94) - 1)
                            end;
                            p_u_19._sfx_manager:play_sfx(v_u_14.SFX_FANFARE)
                            l__menus_0:push_menu(v_u_7:new(p_u_19, l__spui_0, l__menus_0):set_text("Upgrade success!", v97))
                        end)
                    else
                        l__menus_0:remove_menu(v_u_88)
                        l__menus_0:push_menu(v_u_7:new(p_u_19, l__spui_0, l__menus_0):set_text("Upgrade failed.", p_u_90))
                        v_u_5:ptry(function() --[[ Line: 331 ]]
                            --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_89, (copy 3): p_u_90 ]]
                            v_u_6:warnf("_shop_local_protocol:try_craft_gear_upgrade success fail [%s](%s) [%s](%s)", typeof(p_u_89), tostring(p_u_89), typeof(p_u_90), (tostring(p_u_90)))
                        end)
                    end;
                end)
            end, function(p98, p99) --[[ Line: 366 ]]
                --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_8 ]]
                return v_u_8:singleton():upgrade_count_can_upgrade((v_u_13:get_ownedid_upgrade_count(p98, p99)));
            end))
        end;
        v22.is_search_section_enabled = function(_) --[[ Name: is_search_section_enabled ]] --[[ Line: 373 ]]
            return true;
        end;
        v22.get_category_names = function(_) --[[ Name: get_category_names ]] --[[ Line: 374 ]]
            return "Name", "Count";
        end;
        v22:cons()
        return v22;
    end
};
