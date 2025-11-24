-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:52 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Lobby.UI.CraftingUITabBase)
local v_u_2 = require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_3 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
local v_u_4 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_5 = require(game.ReplicatedStorage.Crafting.CraftingMaterialBase)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_7 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_8 = require(game.ReplicatedStorage.PlayerInfo.BoxInfo)
require(game.ReplicatedStorage.Crafting.ColorTierMaterial)
local v_u_9 = require(game.ReplicatedStorage.Pets.PetUtils)
local v_u_10 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_11 = require(game.ReplicatedStorage.PlayerInfo.LeaderboardTicketRewardUtil)
local v_u_12 = require(game.ReplicatedStorage.Lobby.UI.CraftingUISearchSection)
local v13 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_14 = nil
local v_u_15 = nil
local v_u_16 = nil
v13:require_client(function() --[[ Line: 21 ]]
    --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_15, (ref 3): v_u_16 ]]
    v_u_14 = require(game.ReplicatedStorage.Lobby.UI.CraftingUITabGear)
    v_u_15 = require(game.ReplicatedStorage.LocalShared.LocalFeverIconUtil)
    v_u_16 = require(game.ReplicatedStorage.Lobby.Menus.TrainPetUI)
end)
return {
    ["Tab"] = "CraftingUITabMaterials",
    ["new"] = function(_, p_u_17, p_u_18, p_u_19) --[[ Name: new ]] --[[ Line: 31 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_3, (copy 3): v_u_10, (copy 4): v_u_2, (copy 5): v_u_12, (copy 6): v_u_4, (copy 7): v_u_6, (copy 8): v_u_5, (ref 9): v_u_15, (ref 10): v_u_14, (ref 11): v_u_16, (copy 12): v_u_8, (copy 13): v_u_11, (copy 14): v_u_9, (copy 15): v_u_7 ]]
        local v_u_20 = v_u_1:new()
        local v_u_21 = nil
        local v_u_22 = nil
        local v_u_23 = nil
        local v_u_24 = nil
        local v_u_25 = nil
        local v_u_26 = 1
        local v_u_27 = 0
        local function _() --[[ Name: cons ]] --[[ Line: 43 ]]
            --[[ Upvalues: (ref 1): v_u_21, (copy 2): p_u_19, (ref 3): v_u_22, (ref 4): v_u_23, (ref 5): v_u_24, (ref 6): v_u_25, (copy 7): v_u_20 ]]
            v_u_21 = p_u_19.PrimaryPart.SurfaceGui.Frame.SelectedInfoSection.CraftingUITabMaterials
            v_u_22 = v_u_21.IconFrame.Icon
            v_u_23 = v_u_21.NameDisplay
            v_u_24 = v_u_21.DescriptionDisplay
            v_u_25 = v_u_21.OwnedDisplay
            v_u_20:clear_selected_display()
        end;
        local v_u_28 = v_u_3:invalid_material_id()
        local function _() --[[ Name: reset_use_button_display ]] --[[ Line: 54 ]]
            --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_10, (copy 3): p_u_18 ]]
            v_u_26 = 1
            for _, v29 in v_u_10:get_list_of_children_of_classname(p_u_18:get_use_button():get_part(), "TextLabel"):key_itr() do
                v29.Text = "Use"
            end;
        end;
        v_u_20.clear_selected_display = function(_) --[[ Name: clear_selected_display ]] --[[ Line: 62 ]]
            --[[ Upvalues: (ref 1): v_u_28, (ref 2): v_u_3, (ref 3): v_u_22, (ref 4): v_u_10, (ref 5): v_u_23, (ref 6): v_u_24, (ref 7): v_u_25, (ref 8): v_u_26, (copy 9): p_u_18 ]]
            v_u_28 = v_u_3:invalid_material_id()
            v_u_22.Image = v_u_10:transparent_assetid()
            v_u_23.Text = ""
            v_u_24.Text = ""
            v_u_25.Text = "-"
            v_u_26 = 1
            v_u_26 = 1
            for _, v30 in v_u_10:get_list_of_children_of_classname(p_u_18:get_use_button():get_part(), "TextLabel"):key_itr() do
                v30.Text = "Use"
            end;
        end;
        v_u_20.set_visible = function(_, p31) --[[ Name: set_visible ]] --[[ Line: 72 ]]
            --[[ Upvalues: (ref 1): v_u_21, (copy 2): p_u_18 ]]
            v_u_21.Visible = p31
            if p31 then
                p_u_18:get_craft_button():set_visible(false)
                p_u_18:get_use_button():set_visible(true)
                p_u_18:get_use_button():set_enabled(false)
            end;
        end;
        v_u_20.get_list_elements = function(_) --[[ Name: get_list_elements ]] --[[ Line: 81 ]]
            --[[ Upvalues: (copy 1): p_u_17, (ref 2): v_u_2, (copy 3): p_u_18, (ref 4): v_u_3, (ref 5): v_u_12, (ref 6): v_u_4 ]]
            local v_u_32 = v_u_2:get_owned_crafting_materials((p_u_17._player_blob_manager:get_player_blob())):key_list()
            local v_u_33 = string.lower(p_u_18:get_search_name())
            v_u_32:remove_if(function(p34, _) --[[ Line: 87 ]]
                --[[ Upvalues: (ref 1): v_u_3, (copy 2): v_u_33 ]]
                return string.find(string.lower((v_u_3:singleton():get_material_name(p34))), v_u_33, 1, true) == nil;
            end)
            local v43, v44 = pcall(function() --[[ Line: 92 ]]
                --[[ Upvalues: (ref 1): p_u_18, (ref 2): v_u_12, (copy 3): v_u_32, (ref 4): v_u_3 ]]
                if p_u_18:get_sort_type() == v_u_12.SortType.Category1 then
                    local function f_material_type_sort(p35, p36) --[[ Name: material_type_sort ]] --[[ Line: 94 ]]
                        --[[ Upvalues: (ref 1): v_u_12 ]]
                        return v_u_12:materialid_get_type_sort_value(p36) > v_u_12:materialid_get_type_sort_value(p35) == false and -1 or 1;
                    end;
                    local function f_material_type_sort_inverse(p37, p38) --[[ Name: material_type_sort_inverse ]] --[[ Line: 99 ]]
                        --[[ Upvalues: (ref 1): v_u_12 ]]
                        return (v_u_12:materialid_get_type_sort_value(p38) > v_u_12:materialid_get_type_sort_value(p37) == false and -1 or 1) * -1;
                    end;
                    if p_u_18:get_sort_order() == v_u_12.SortOrder.Ascending then
                        v_u_32:sort(f_material_type_sort)
                    else
                        v_u_32:sort(f_material_type_sort_inverse)
                    end;
                else
                    if p_u_18:get_sort_type() == v_u_12.SortType.Category2 then
                        local function f_material_name_sort(p39, p40) --[[ Name: material_name_sort ]] --[[ Line: 109 ]]
                            --[[ Upvalues: (ref 1): v_u_3 ]]
                            return v_u_3:singleton():get_material_name(p40) > v_u_3:singleton():get_material_name(p39) == false and -1 or 1;
                        end;
                        local function f_material_name_sort_inverse(p41, p42) --[[ Name: material_name_sort_inverse ]] --[[ Line: 114 ]]
                            --[[ Upvalues: (ref 1): v_u_3 ]]
                            return (v_u_3:singleton():get_material_name(p42) > v_u_3:singleton():get_material_name(p41) == false and -1 or 1) * -1;
                        end;
                        if p_u_18:get_sort_order() == v_u_12.SortOrder.Ascending then
                            v_u_32:sort(f_material_name_sort)
                            return;
                        end;
                        v_u_32:sort(f_material_name_sort_inverse)
                    end;
                    return;
                end;
            end)
            if not v43 then
                v_u_4:warnf("CraftingUITabMaterials:get_list_elements err(%s)", (tostring(v44)))
            end;
            return v_u_32;
        end;
        v_u_20.get_empty_text = function(_) --[[ Name: get_empty_text ]] --[[ Line: 144 ]]
            return "You don\'t own any crafting materials. Acquire them from the Note Machine and Marketplace!";
        end;
        v_u_20.redraw_list = function(p45) --[[ Name: redraw_list ]] --[[ Line: 148 ]]
            --[[ Upvalues: (copy 1): p_u_18, (copy 2): p_u_17, (ref 3): v_u_2, (ref 4): v_u_27, (ref 5): v_u_3 ]]
            p_u_18:clear_list()
            local v46 = v_u_2:get_owned_crafting_materials((p_u_17._player_blob_manager:get_player_blob()))
            local v47 = p45:get_list_elements()
            if v47:count() == 0 then
                p_u_18:set_empty_display_visible(true)
            end;
            local v48 = p_u_18:get_list_elements()
            for v49 = 1, v48:count() do
                local v50 = v48:get(v49)
                local v51 = v_u_27 * v48:count() + v49
                if v51 <= v47:count() then
                    local v52 = v47:get(v51)
                    v50:set_info(v52, v_u_3:singleton():get_material_icon(v52), (v46:get(v52)))
                    v50:set_visible(true)
                end;
            end;
        end;
        v_u_20.page_up = function(p53) --[[ Name: page_up ]] --[[ Line: 178 ]]
            --[[ Upvalues: (ref 1): v_u_27 ]]
            v_u_27 = v_u_27 - 1
            p53:redraw_list()
        end;
        v_u_20.page_down = function(p54) --[[ Name: page_down ]] --[[ Line: 183 ]]
            --[[ Upvalues: (ref 1): v_u_27 ]]
            v_u_27 = v_u_27 + 1
            p54:redraw_list()
        end;
        v_u_20.can_page_up = function(_) --[[ Name: can_page_up ]] --[[ Line: 188 ]]
            --[[ Upvalues: (ref 1): v_u_27 ]]
            return v_u_27 > 0;
        end;
        v_u_20.reset_page = function(_) --[[ Name: reset_page ]] --[[ Line: 192 ]]
            --[[ Upvalues: (ref 1): v_u_27 ]]
            v_u_27 = 0
        end;
        v_u_20.can_page_down = function(p55) --[[ Name: can_page_down ]] --[[ Line: 194 ]]
            --[[ Upvalues: (ref 1): v_u_27, (copy 2): p_u_18 ]]
            return (v_u_27 + 1) * p_u_18:get_list_elements():count() < p55:get_list_elements():count();
        end;
        local v56 = v_u_6:new()
        local v57 = {}
        v57[v_u_5.Type.FeverIcon] = function() --[[ Line: 199 ]]
            --[[ Upvalues: (ref 1): v_u_15, (copy 2): p_u_17, (ref 3): v_u_3, (ref 4): v_u_28 ]]
            v_u_15:set_selected_fever_icon(p_u_17, v_u_3:singleton():get_material(v_u_28):get_fever_icon_id())
        end
        v57[v_u_5.Type.Blueprint] = function() --[[ Line: 202 ]]
            --[[ Upvalues: (copy 1): p_u_18, (ref 2): v_u_14 ]]
            p_u_18:set_current_tab_and_update(v_u_14.Tab)
        end
        v57[v_u_5.Type.Pet] = function() --[[ Line: 205 ]]
            --[[ Upvalues: (ref 1): v_u_16, (copy 2): p_u_17, (ref 3): v_u_28 ]]
            v_u_16:use_pet_materialid(p_u_17, v_u_28)
        end
        v57[v_u_5.Type.Box] = function() --[[ Line: 208 ]]
            --[[ Upvalues: (ref 1): v_u_8, (copy 2): p_u_17, (ref 3): v_u_28, (ref 4): v_u_26 ]]
            v_u_8:client_use_box_materialid(p_u_17, v_u_28, v_u_26)
        end
        v57[v_u_5.Type.LeaderboardTicket] = function() --[[ Line: 211 ]]
            --[[ Upvalues: (ref 1): v_u_11, (copy 2): p_u_17 ]]
            v_u_11:client_show_menu(p_u_17)
        end
        local v_u_58 = v56:add_table(v57)
        local v59 = v_u_6:new()
        local v60 = {}
        v60[v_u_5.Type.Pet] = function() --[[ Line: 219 ]]
            --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_28, (copy 3): p_u_17, (ref 4): v_u_9 ]]
            local v61, _ = v_u_9:playerblob_can_add_pet_of_petid(p_u_17._player_blob_manager:get_player_blob(), (v_u_3:singleton():get_material(v_u_28):get_pet_id()))
            return v61, false, 1;
        end
        v60[v_u_5.Type.Box] = function() --[[ Line: 225 ]]
            --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_28 ]]
            local v62 = v_u_8:get_materialid_box_type(v_u_28)
            return true, v_u_8:box_type_multiple_use_enabled(v62), v_u_8:box_type_use_max_count(v62);
        end
        v60[v_u_5.Type.FeverIcon] = function(_) --[[ Line: 230 ]]
            --[[ Upvalues: (copy 1): p_u_17, (ref 2): v_u_15, (ref 3): v_u_3, (ref 4): v_u_28 ]]
            return v_u_15:playerblob_get_fevericon((p_u_17._player_blob_manager:get_player_blob())) ~= v_u_3:singleton():get_material(v_u_28):get_fever_icon_id(), false, 1;
        end
        local v_u_63 = v59:add_table(v60)
        local function f_get_selected_material_owned_count() --[[ Name: get_selected_material_owned_count ]] --[[ Line: 236 ]]
            --[[ Upvalues: (ref 1): v_u_28, (ref 2): v_u_3, (ref 3): v_u_2, (copy 4): p_u_17 ]]
            return v_u_28 == v_u_3:invalid_material_id() and 0 or v_u_2:get_count_of_material(p_u_17._player_blob_manager:get_player_blob(), v_u_28);
        end;
        local function f_get_selected_material_use_button_status() --[[ Name: get_selected_material_use_button_status ]] --[[ Line: 241 ]]
            --[[ Upvalues: (ref 1): v_u_28, (ref 2): v_u_3, (copy 3): v_u_58, (copy 4): v_u_63, (ref 5): v_u_2, (copy 6): p_u_17 ]]
            if v_u_28 == v_u_3:invalid_material_id() then
                return false, false;
            end;
            local v64 = v_u_3:singleton():get_material_type(v_u_28)
            local v65 = v_u_58:contains(v64)
            local v66, v67
            if v65 and v_u_63:contains(v64) then
                v65, v66, v67 = v_u_63:get(v64)()
            else
                v67 = -1
                v66 = false
            end;
            if v67 == -1 then
                v67 = v_u_28 == v_u_3:invalid_material_id() and 0 or v_u_2:get_count_of_material(p_u_17._player_blob_manager:get_player_blob(), v_u_28)
            end;
            return v65, v66, math.min(v_u_28 == v_u_3:invalid_material_id() and 0 or v_u_2:get_count_of_material(p_u_17._player_blob_manager:get_player_blob(), v_u_28), v67);
        end;
        local function f_update_use_amount_display() --[[ Name: update_use_amount_display ]] --[[ Line: 258 ]]
            --[[ Upvalues: (copy 1): f_get_selected_material_use_button_status, (ref 2): v_u_10, (copy 3): p_u_18, (ref 4): v_u_26 ]]
            local _, v68 = f_get_selected_material_use_button_status()
            if v68 then
                for _, v69 in v_u_10:get_list_of_children_of_classname(p_u_18:get_use_button():get_part(), "TextLabel"):key_itr() do
                    v69.Text = string.format("Use x%d", v_u_26)
                end;
            else
                v_u_26 = 1
                for _, v70 in v_u_10:get_list_of_children_of_classname(p_u_18:get_use_button():get_part(), "TextLabel"):key_itr() do
                    v70.Text = "Use"
                end;
            end;
        end;
        v_u_20.list_element_pressed = function(_, _, p71) --[[ Name: list_element_pressed ]] --[[ Line: 270 ]]
            --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_4, (ref 3): v_u_28, (ref 4): v_u_26, (ref 5): v_u_22, (ref 6): v_u_23, (ref 7): v_u_24, (ref 8): v_u_25, (copy 9): f_get_selected_material_owned_count, (copy 10): f_get_selected_material_use_button_status, (copy 11): f_update_use_amount_display, (copy 12): p_u_18 ]]
            if v_u_3:singleton():get_material(p71) == nil then
                v_u_4:errf("CraftingUITabMaterials list_element_pressed invalid data(%s)", (tostring(p71)))
            end;
            if v_u_28 ~= p71 then
                v_u_26 = 1
            end;
            v_u_28 = p71
            v_u_22.Image = v_u_3:singleton():get_material_icon(p71)
            v_u_23.Text = v_u_3:singleton():get_material_name(p71)
            v_u_23.TextColor3 = v_u_3:singleton():tier_get_color(v_u_3:singleton():get_material_tier(p71))
            v_u_24.Text = v_u_3:singleton():get_material_description(p71)
            v_u_25.Text = string.format("%d", f_get_selected_material_owned_count())
            local v72, _ = f_get_selected_material_use_button_status()
            f_update_use_amount_display()
            p_u_18:get_use_button():set_enabled(v72)
            p_u_18:set_on_refocus_selected_element(p71)
        end;
        v_u_20.show_use_amount_buttons = function(_) --[[ Name: show_use_amount_buttons ]] --[[ Line: 291 ]]
            --[[ Upvalues: (copy 1): f_get_selected_material_use_button_status, (ref 2): v_u_26 ]]
            local v73, v74, v75 = f_get_selected_material_use_button_status()
            if v73 == true and v74 == true then
                return v_u_26 > 1, v_u_26 < v75;
            else
                return false, false;
            end;
        end;
        v_u_20.craft_amount_button_pressed = function(_, p76) --[[ Name: craft_amount_button_pressed ]] --[[ Line: 296 ]]
            --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_10, (copy 3): f_get_selected_material_owned_count, (copy 4): f_update_use_amount_display ]]
            v_u_26 = v_u_10:clamp(v_u_26 + p76, 1, f_get_selected_material_owned_count())
            f_update_use_amount_display()
        end;
        v_u_20.select_element = function(p77, p78) --[[ Name: select_element ]] --[[ Line: 301 ]]
            --[[ Upvalues: (copy 1): p_u_18, (ref 2): v_u_27, (ref 3): v_u_4 ]]
            local v79 = p77:get_list_elements():find(p78)
            if v79 ~= -1 then
                local v80 = p_u_18:get_list_elements()
                v_u_27 = math.floor((v79 - 1) / v80:count())
                p_u_18:update_current_tab()
                local v81 = v79 - v_u_27 * v80:count()
                if v81 <= 0 or v80:count() < v81 then
                    return v_u_4:warnf("CraftingUITabSongs:select_element invalid select_element_index(%s)", (tostring(v81)));
                end;
                p_u_18:list_element_pressed(v80:get(v81), v81, p78)
            end;
        end;
        v_u_20.craft_pressed = function(_) --[[ Name: craft_pressed ]] --[[ Line: 325 ]]
            --[[ Upvalues: (copy 1): p_u_17, (ref 2): v_u_7, (ref 3): v_u_28, (ref 4): v_u_3, (ref 5): v_u_4, (copy 6): v_u_58 ]]
            p_u_17._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            if v_u_28 == v_u_3:invalid_material_id() then
                return v_u_4:warnf("CraftingUITabMaterials invalid material id selected");
            end;
            if v_u_58:contains(v_u_3:singleton():get_material_type(v_u_28)) ~= true then
                return v_u_4:warnf("CraftingUITabMaterials craft_pressed no in _material_type_to_craft_action");
            end;
            v_u_58:get(v_u_3:singleton():get_material_type(v_u_28))()
        end;
        v_u_20.is_search_section_enabled = function(_) --[[ Name: is_search_section_enabled ]] --[[ Line: 333 ]]
            return true;
        end;
        v_u_20.get_category_names = function(_) --[[ Name: get_category_names ]] --[[ Line: 334 ]]
            return "Type", "Name";
        end;
        v_u_21 = p_u_19.PrimaryPart.SurfaceGui.Frame.SelectedInfoSection.CraftingUITabMaterials
        v_u_22 = v_u_21.IconFrame.Icon
        local _ = v_u_21.NameDisplay
        v_u_24 = v_u_21.DescriptionDisplay
        v_u_25 = v_u_21.OwnedDisplay
        v_u_20:clear_selected_display()
        return v_u_20;
    end
};
