-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:51 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Lobby.UI.CraftingUITabBase)
local v_u_2 = require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_3 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_6 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_7 = require(game.ReplicatedStorage.Lobby.UI.MaterialsRequiredDisplay)
local v_u_8 = require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_9 = require(game.ReplicatedStorage.Avatar.GearStatsDescriptions)
local v_u_10 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentDatabase)
local v_u_11 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_12 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_13 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_14 = require(game.ReplicatedStorage.Lobby.UI.GearEquipV2UI.GearEquipV2GearStatDisplay)
local v_u_15 = require(game.ReplicatedStorage.Tutorial.GearCraftingTutorialInfo)
local v_u_16 = require(game.ReplicatedStorage.Lobby.UI.CraftingUISearchSection)
local v17 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_18 = nil
v17:require_client(function() --[[ Line: 24 ]]
    --[[ Upvalues: (ref 1): v_u_18 ]]
    v_u_18 = require(game.ReplicatedStorage.Tutorial.Menus.GearCraftingTutorialUI)
end)
return {
    ["Tab"] = "CraftingUITabGear",
    ["new"] = function(_, p_u_19, p_u_20, p_u_21) --[[ Name: new ]] --[[ Line: 31 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_4, (copy 3): v_u_7, (copy 4): v_u_3, (copy 5): v_u_2, (copy 6): v_u_15, (copy 7): v_u_16, (copy 8): v_u_11, (copy 9): v_u_5, (copy 10): v_u_10, (copy 11): v_u_8, (copy 12): v_u_13, (copy 13): v_u_14, (copy 14): v_u_9, (copy 15): v_u_6, (copy 16): v_u_12, (ref 17): v_u_18 ]]
        local v22 = v_u_1:new()
        local l__spui_0 = p_u_19._spui
        local l__menus_0 = p_u_19._menus
        local v_u_23 = nil
        local v_u_24 = nil
        local v_u_25 = nil
        local v_u_26 = v_u_4:new()
        local v_u_27 = v_u_4:new()
        local v_u_28 = v_u_4:new()
        local v_u_29 = 0
        local v_u_30 = -1
        local v_u_31 = nil
        local v_u_32 = nil
        v22.cons = function(p33) --[[ Name: cons ]] --[[ Line: 50 ]]
            --[[ Upvalues: (ref 1): v_u_23, (copy 2): p_u_21, (ref 3): v_u_24, (ref 4): v_u_25, (ref 5): v_u_31, (ref 6): v_u_32, (copy 7): v_u_26, (ref 8): v_u_7, (copy 9): v_u_27, (copy 10): v_u_28 ]]
            v_u_23 = p_u_21.PrimaryPart.SurfaceGui.Frame.SelectedInfoSection.CraftingUITabGear
            v_u_24 = v_u_23.NameDisplay
            v_u_25 = v_u_23.IconFrame.Icon
            v_u_31 = v_u_23.SlotIcon
            v_u_32 = v_u_23.SlotDisplay
            v_u_32.Visible = false
            v_u_31.Visible = false
            v_u_26:push_back(v_u_7:new(v_u_23.RequirementDisplay1))
            v_u_26:push_back(v_u_7:new(v_u_23.RequirementDisplay2))
            v_u_26:push_back(v_u_7:new(v_u_23.RequirementDisplay3))
            v_u_26:push_back(v_u_7:new(v_u_23.RequirementDisplay4))
            v_u_27:push_back_table_list({
                v_u_23.StatDisplay1,
                v_u_23.StatDisplay2,
                v_u_23.StatDisplay3,
                v_u_23.StatDisplay4
            })
            v_u_28:push_back_table_list({
                v_u_23.StatDescription1,
                v_u_23.StatDescription2,
                v_u_23.StatDescription3,
                v_u_23.StatDescription4
            })
            p33:clear_selected_display()
        end;
        v22.clear_selected_display = function(_) --[[ Name: clear_selected_display ]] --[[ Line: 82 ]]
            --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_25, (copy 3): v_u_27, (copy 4): v_u_28, (copy 5): v_u_26, (ref 6): v_u_30, (copy 7): p_u_20 ]]
            v_u_24.Text = ""
            v_u_25.Image = ""
            for v34 = 1, v_u_27:count() do
                v_u_27:get(v34).Visible = false
                v_u_28:get(v34).Visible = false
            end;
            for v35 = 1, v_u_26:count() do
                v_u_26:get(v35):set_visible(false)
            end;
            v_u_30 = -1
            p_u_20:get_craft_button():set_enabled(false)
        end;
        v22.set_visible = function(_, p36) --[[ Name: set_visible ]] --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_23, (copy 2): p_u_20 ]]
            v_u_23.Visible = p36
            if p36 then
                p_u_20:get_craft_button():set_visible(true)
                p_u_20:get_craft_button():set_enabled(false)
                p_u_20:get_use_button():set_visible(false)
            end;
        end;
        v22.get_elements_list = function(_) --[[ Name: get_elements_list ]] --[[ Line: 105 ]]
            --[[ Upvalues: (copy 1): p_u_19, (ref 2): v_u_4, (ref 3): v_u_3, (ref 4): v_u_2, (ref 5): v_u_15, (copy 6): p_u_20, (ref 7): v_u_16, (ref 8): v_u_11 ]]
            local v_u_37 = p_u_19._player_blob_manager:get_player_blob()
            local v38 = v_u_4:new()
            for v39, v40 in v_u_3:singleton():gear_recipe_key_itr() do
                local v41, v42 = v40:has_display_requirement_materialid()
                if v41 == true then
                    if v_u_2:get_count_of_material(v_u_37, v42) > 0 then
                        v38:push_back(v39)
                    end;
                else
                    v38:push_back(v39)
                end;
            end;
            v38:remove_if(function(p43) --[[ Line: 118 ]]
                --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_15, (copy 3): v_u_37 ]]
                if v_u_3:singleton():get_gear_recipe(p43):is_gear_tutorial() then
                    return not (v_u_15:has_any_equipped_gear(v_u_37) and (v_u_15:has_any_gear_upgrades(v_u_37) and v_u_15:playerblob_is_gear_tutorial_active(v_u_37)));
                else
                    return false;
                end;
            end)
            local v44 = v_u_4:new()
            local v45 = v_u_4:new()
            local v46 = v_u_4:new()
            for v47 = 1, v38:count() do
                local v48 = v38:get(v47)
                if v_u_2:can_craft_requirements_dict(v_u_37, v_u_3:singleton():get_gear_recipe_requirements_dict(v48)) then
                    v45:push_back(v48)
                else
                    v46:push_back(v48)
                end;
            end;
            local function f_sort_filter_recipe_id_list(p49) --[[ Name: sort_filter_recipe_id_list ]] --[[ Line: 146 ]]
                --[[ Upvalues: (ref 1): p_u_20, (ref 2): v_u_3, (ref 3): v_u_16, (ref 4): v_u_11, (copy 5): v_u_37 ]]
                local v_u_50 = string.lower(p_u_20:get_search_name())
                p49:remove_if(function(p51, _) --[[ Line: 148 ]]
                    --[[ Upvalues: (ref 1): v_u_3, (copy 2): v_u_50 ]]
                    return string.find(string.lower((v_u_3:singleton():get_gear_recipe_name(p51))), v_u_50, 1, true) == nil;
                end)
                if p_u_20:get_sort_type() == v_u_16.SortType.Category1 then
                    local function f_gear_name_sort(p52, p53) --[[ Name: gear_name_sort ]] --[[ Line: 153 ]]
                        --[[ Upvalues: (ref 1): v_u_3 ]]
                        return v_u_3:singleton():get_gear_recipe_name(p52) < v_u_3:singleton():get_gear_recipe_name(p53) == false and -1 or 1;
                    end;
                    local function f_gear_name_sort_inverse(p54, p55) --[[ Name: gear_name_sort_inverse ]] --[[ Line: 158 ]]
                        --[[ Upvalues: (ref 1): v_u_3 ]]
                        return (v_u_3:singleton():get_gear_recipe_name(p54) < v_u_3:singleton():get_gear_recipe_name(p55) == false and -1 or 1) * -1;
                    end;
                    if p_u_20:get_sort_order() == v_u_16.SortOrder.Ascending then
                        p49:sort(f_gear_name_sort)
                    else
                        p49:sort(f_gear_name_sort_inverse)
                    end;
                else
                    if p_u_20:get_sort_type() == v_u_16.SortType.Category2 then
                        local function f_craft_count_sort(p56, p57) --[[ Name: craft_count_sort ]] --[[ Line: 168 ]]
                            --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_37, (ref 3): v_u_3 ]]
                            return v_u_11:playerblob_get_owned_count_of_equipmentid(v_u_37, v_u_3:singleton():get_gear_recipe(p57):get_gear_id()) - v_u_11:playerblob_get_owned_count_of_equipmentid(v_u_37, v_u_3:singleton():get_gear_recipe(p56):get_gear_id());
                        end;
                        local function f_craft_count_sort_inverse(p58, p59) --[[ Name: craft_count_sort_inverse ]] --[[ Line: 173 ]]
                            --[[ Upvalues: (copy 1): f_craft_count_sort ]]
                            return f_craft_count_sort(p58, p59) * -1;
                        end;
                        if p_u_20:get_sort_order() == v_u_16.SortOrder.Ascending then
                            p49:sort(f_craft_count_sort)
                            return;
                        end;
                        p49:sort(f_craft_count_sort_inverse)
                    end;
                    return;
                end;
            end;
            f_sort_filter_recipe_id_list(v45)
            f_sort_filter_recipe_id_list(v46)
            v44:push_back_from_list(v45)
            v44:push_back_from_list(v46)
            return v44;
        end;
        v22.get_empty_text = function(_) --[[ Name: get_empty_text ]] --[[ Line: 194 ]]
            return "No available gear crafting recipes. Craftable gear will show up here when you own any of the prerequisite materials.";
        end;
        v22.redraw_list = function(p60) --[[ Name: redraw_list ]] --[[ Line: 198 ]]
            --[[ Upvalues: (copy 1): p_u_20, (copy 2): p_u_19, (ref 3): v_u_29, (ref 4): v_u_3, (ref 5): v_u_11, (ref 6): v_u_2 ]]
            p_u_20:clear_list()
            local v61 = p_u_19._player_blob_manager:get_player_blob()
            local v62 = p60:get_elements_list()
            if v62:count() == 0 then
                p_u_20:set_empty_display_visible(true)
            end;
            local v63 = p_u_20:get_list_elements()
            for v64 = 1, v63:count() do
                local v65 = v63:get(v64)
                local v66 = v_u_29 * v63:count() + v64
                if v66 <= v62:count() then
                    local v67 = v62:get(v66)
                    local v68 = v_u_3:singleton():get_gear_recipe_requirements_dict(v67)
                    v65:set_visible(true)
                    v65:set_info(v67, v_u_3:singleton():get_gear_recipe_icon(v67), v_u_11:playerblob_get_owned_count_of_equipmentid(v61, v_u_3:singleton():get_gear_recipe(v67):get_gear_id()))
                    if v_u_3:singleton():get_gear_recipe(v67):is_gear_tutorial() then
                        v65:set_extra_info_icon("rbxassetid://6276704655")
                    end;
                    if v_u_2:can_craft_requirements_dict(v61, v68) then
                        v65:set_alpha(1)
                    else
                        v65:set_alpha(0.35)
                    end;
                end;
            end;
        end;
        v22.page_up = function(p69) --[[ Name: page_up ]] --[[ Line: 236 ]]
            --[[ Upvalues: (ref 1): v_u_29 ]]
            v_u_29 = v_u_29 - 1
            p69:redraw_list()
        end;
        v22.page_down = function(p70) --[[ Name: page_down ]] --[[ Line: 241 ]]
            --[[ Upvalues: (ref 1): v_u_29 ]]
            v_u_29 = v_u_29 + 1
            p70:redraw_list()
        end;
        v22.can_page_up = function(_) --[[ Name: can_page_up ]] --[[ Line: 246 ]]
            --[[ Upvalues: (ref 1): v_u_29 ]]
            return v_u_29 > 0;
        end;
        v22.reset_page = function(_) --[[ Name: reset_page ]] --[[ Line: 250 ]]
            --[[ Upvalues: (ref 1): v_u_29 ]]
            v_u_29 = 0
        end;
        v22.can_page_down = function(p71) --[[ Name: can_page_down ]] --[[ Line: 252 ]]
            --[[ Upvalues: (ref 1): v_u_29, (copy 2): p_u_20 ]]
            return (v_u_29 + 1) * p_u_20:get_list_elements():count() < p71:get_elements_list():count();
        end;
        v22.get_top_stats = function(_, p72) --[[ Name: get_top_stats ]] --[[ Line: 256 ]]
            --[[ Upvalues: (ref 1): v_u_4 ]]
            local v73 = v_u_4:new()
            for v74, v75 in pairs(p72) do
                v73:push_back({
                    ["Stat"] = v74,
                    ["Value"] = v75
                })
            end;
            v73:sort(function(p76, p77) --[[ Line: 264 ]]
                return math.abs(p76.Value) - math.abs(p77.Value);
            end)
            return v73;
        end;
        v22.list_element_pressed = function(p78, _, p79) --[[ Name: list_element_pressed ]] --[[ Line: 270 ]]
            --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_5, (ref 3): v_u_30, (copy 4): p_u_19, (ref 5): v_u_10, (ref 6): v_u_24, (ref 7): v_u_8, (ref 8): v_u_25, (ref 9): v_u_32, (ref 10): v_u_31, (ref 11): v_u_13, (copy 12): v_u_27, (copy 13): v_u_28, (ref 14): v_u_14, (ref 15): v_u_9, (copy 16): v_u_26, (ref 17): v_u_2, (copy 18): p_u_20 ]]
            if v_u_3:singleton():get_gear_recipe(p79) == nil then
                v_u_5:errf("CraftingUITabGear list_element_pressed invalid gear_id(%s)", (tostring(p79)))
            end;
            v_u_30 = p79
            local v80 = p_u_19._player_blob_manager:get_player_blob()
            local v81 = v_u_10:singleton():get_equipment_for_id(v_u_3:singleton():get_gear_recipe(v_u_30):get_gear_id())
            v_u_24.Text = v81:get_name()
            v_u_24.TextColor3 = v_u_8:tier_get_color(v81:get_gear_tier())
            v_u_25.Image = v81:get_icon()
            v_u_32.Visible = true
            v_u_31.Visible = true
            v_u_32.Text = v_u_13:slot_to_name(v81:get_avatar_slot())
            v_u_31.Image = v_u_13:slot_to_icon(v81:get_avatar_slot())
            local v82 = p78:get_top_stats(v81:get_gear_statmodifierobj())
            for v83 = 1, v_u_27:count() do
                local v84 = v_u_27:get(v83)
                local v85 = v_u_28:get(v83)
                if v82:count() < v83 then
                    v84.Visible = false
                    v85.Visible = false
                else
                    local l_Stat_0 = v82:get(v83).Stat
                    local l_Value_0 = v82:get(v83).Value
                    v84.Visible = true
                    v85.Visible = true
                    v84.Text = string.format("%s%d %s", l_Value_0 < 0 and "-" or "+", math.abs(l_Value_0), (v_u_8:type_to_name(l_Stat_0)))
                    v84.TextColor3 = v_u_8:gear_attrvalue_opts_get_color(l_Value_0, l_Stat_0, false)
                    v_u_14:display_stat_icon_for_sub_text(v84, l_Stat_0, 4)
                    v85.Text = v_u_9:get_description_for_stat(l_Stat_0)
                end;
            end;
            for v86 = 1, v_u_26:count() do
                v_u_26:get(v86):set_visible(false)
            end;
            local v87 = v_u_3:singleton():get_gear_recipe_requirements_dict(v_u_30)
            local v88 = v87:key_list()
            for v89 = 1, v_u_26:count() do
                if v88:count() < v89 then
                    break;
                end;
                local v90 = v88:get(v89)
                local v91 = v_u_26:get(v89)
                v91:set_visible(true)
                v91:set_info(v_u_3:singleton():get_material_name(v90), v_u_3:singleton():get_material_icon(v90), v_u_3:singleton():tier_get_color(v_u_3:singleton():get_material_tier(v90)), v_u_2:get_count_of_material(v80, v90), v87:get(v90))
            end;
            p_u_20:get_craft_button():set_enabled(v_u_2:can_craft_requirements_dict(v80, v87))
        end;
        v22.craft_pressed = function(p_u_92) --[[ Name: craft_pressed ]] --[[ Line: 341 ]]
            --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_30, (copy 3): l__menus_0, (ref 4): v_u_6, (copy 5): p_u_19, (copy 6): l__spui_0, (ref 7): v_u_12, (ref 8): v_u_18 ]]
            if v_u_3:singleton():get_gear_recipe(v_u_30) == nil then
                return l__menus_0:push_menu(v_u_6:new(p_u_19, l__spui_0, l__menus_0):set_text("Failed", "No gear selected"));
            end;
            p_u_19._sfx_manager:play_sfx(v_u_12.SFX_BUTTONPRESS)
            local v_u_93 = l__menus_0:push_menu(v_u_6:new(p_u_19, l__spui_0, l__menus_0):set_text("Crafting...", ""):set_close_button_visible(false))
            p_u_19._shop_local_protocol:try_craft_gear(v_u_30, function(p94, p95) --[[ Line: 348 ]]
                --[[ Upvalues: (ref 1): l__menus_0, (copy 2): v_u_93, (ref 3): v_u_6, (ref 4): p_u_19, (ref 5): l__spui_0, (ref 6): v_u_30, (copy 7): p_u_92, (ref 8): v_u_12, (ref 9): v_u_3, (ref 10): v_u_18 ]]
                if p94 == true then
                    p_u_19._player_blob_manager:do_sync(function(_) --[[ Line: 355 ]]
                        --[[ Upvalues: (ref 1): v_u_30, (ref 2): p_u_92, (ref 3): p_u_19, (ref 4): v_u_12, (ref 5): l__menus_0, (ref 6): v_u_93, (ref 7): v_u_3, (ref 8): v_u_18, (ref 9): l__spui_0, (ref 10): v_u_6 ]]
                        local v96 = v_u_30
                        p_u_92:clear_selected_display()
                        p_u_92:redraw_list()
                        p_u_19._sfx_manager:play_sfx(v_u_12.SFX_ACQUIRE)
                        l__menus_0:remove_menu(v_u_93)
                        if v_u_3:singleton():get_gear_recipe(v96):is_gear_tutorial() then
                            for _, v97 in v_u_18:active_instances():key_itr() do
                                l__menus_0:remove_menu(v97)
                            end;
                            l__menus_0:push_menu(v_u_18:new(p_u_19, l__spui_0, l__menus_0)):go_to_last_page()
                        end;
                        l__menus_0:push_menu(v_u_6:new(p_u_19, l__spui_0, l__menus_0):set_text("Crafted!", string.format("You crafted %s!", v_u_3:singleton():get_gear_recipe_name(v96))))
                    end)
                else
                    l__menus_0:remove_menu(v_u_93)
                    l__menus_0:push_menu(v_u_6:new(p_u_19, l__spui_0, l__menus_0):set_text("Crafting failed.", p95))
                end;
            end)
        end;
        v22.is_search_section_enabled = function(_) --[[ Name: is_search_section_enabled ]] --[[ Line: 379 ]]
            return true;
        end;
        v22.get_category_names = function(_) --[[ Name: get_category_names ]] --[[ Line: 380 ]]
            return "Name", "Count";
        end;
        v22:cons()
        return v22;
    end
};
