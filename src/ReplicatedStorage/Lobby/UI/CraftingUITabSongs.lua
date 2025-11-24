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
local v_u_6 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_7 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_8 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_9 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_10 = require(game.ReplicatedStorage.Lobby.Menus.SongAcquiredV2UI)
local v11 = require(game.ReplicatedStorage.Lobby.UI.MaterialsRequiredDisplay)
local v_u_12 = require(game.ReplicatedStorage.Lobby.UI.CraftingUISearchSection)
local v_u_13 = {
    ["Tab"] = "CraftingUITabSongs",
    ["MaterialsRequiredDisplay"] = v11
}
v_u_13.new = function(_, p_u_14, p_u_15, p_u_16) --[[ Name: new ]] --[[ Line: 19 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_4, (copy 3): v_u_13, (copy 4): v_u_3, (copy 5): v_u_8, (copy 6): v_u_5, (copy 7): v_u_2, (copy 8): v_u_7, (copy 9): v_u_12, (copy 10): v_u_6, (copy 11): v_u_9, (copy 12): v_u_10 ]]
    local v17 = v_u_1:new()
    local l__spui_0 = p_u_14._spui
    local l__menus_0 = p_u_14._menus
    local v_u_18 = nil
    local v_u_19 = nil
    local v_u_20 = nil
    local v_u_21 = nil
    local v_u_22 = nil
    local v_u_23 = nil
    local v_u_24 = nil
    local v_u_25 = v_u_4:new()
    local v_u_26 = 0
    local v_u_27 = -1
    v17.cons = function(p28) --[[ Name: cons ]] --[[ Line: 38 ]]
        --[[ Upvalues: (ref 1): v_u_18, (copy 2): p_u_16, (ref 3): v_u_19, (ref 4): v_u_20, (ref 5): v_u_21, (ref 6): v_u_22, (ref 7): v_u_23, (ref 8): v_u_24, (copy 9): v_u_25, (ref 10): v_u_13 ]]
        v_u_18 = p_u_16.PrimaryPart.SurfaceGui.Frame.SelectedInfoSection.CraftingUITabSongs
        v_u_19 = v_u_18.IconFrame.Icon
        v_u_20 = v_u_18.IconFrame.IconOverlay
        v_u_21 = v_u_18.NameDisplay
        v_u_22 = v_u_18.DescriptionDisplay
        v_u_23 = v_u_18.OwnedDisplay
        v_u_24 = v_u_18.DifficultyDisplay
        v_u_25:push_back(v_u_13.MaterialsRequiredDisplay:new(v_u_18.RequirementDisplay1))
        v_u_25:push_back(v_u_13.MaterialsRequiredDisplay:new(v_u_18.RequirementDisplay2))
        v_u_25:push_back(v_u_13.MaterialsRequiredDisplay:new(v_u_18.RequirementDisplay3))
        v_u_25:push_back(v_u_13.MaterialsRequiredDisplay:new(v_u_18.RequirementDisplay4))
        p28:clear_selected_display()
    end;
    v17.select_element = function(p29, p30) --[[ Name: select_element ]] --[[ Line: 55 ]]
        --[[ Upvalues: (copy 1): p_u_15, (ref 2): v_u_3, (ref 3): v_u_8, (ref 4): v_u_26 ]]
        local v31 = p29:get_song_recipes_list()
        local v32 = p_u_15:get_list_elements()
        local v35 = v31:find(p30, function(p33, p34) --[[ Line: 59 ]]
            --[[ Upvalues: (ref 1): v_u_3 ]]
            return v_u_3:singleton():get_song_recipe_songkey(p33) == p34;
        end)
        if v35 == -1 then
            return v_u_8:warnf("CraftingUITabSongs:select_element can\'t find(%s)", (tostring(p30)));
        end;
        v_u_26 = math.floor((v35 - 1) / v32:count())
        p_u_15:update_current_tab()
        local v36 = v35 - v_u_26 * v32:count()
        if v36 <= 0 or v32:count() < v36 then
            return v_u_8:warnf("CraftingUITabSongs:select_element invalid select_element_index(%s)", (tostring(v36)));
        end;
        local v37 = v32:get(v36)
        p_u_15:list_element_pressed(v37, v36, v37:get_data())
    end;
    v17.clear_selected_display = function(_) --[[ Name: clear_selected_display ]] --[[ Line: 82 ]]
        --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_5, (ref 3): v_u_20, (ref 4): v_u_21, (ref 5): v_u_22, (ref 6): v_u_23, (ref 7): v_u_24, (copy 8): v_u_25, (ref 9): v_u_27, (copy 10): p_u_15 ]]
        v_u_19.Image = v_u_5:transparent_assetid()
        v_u_20.Image = v_u_5:transparent_assetid()
        v_u_21.Text = ""
        v_u_22.Text = ""
        v_u_23.Text = ""
        v_u_24.Text = ""
        for v38 = 1, v_u_25:count() do
            v_u_25:get(v38):set_visible(false)
        end;
        v_u_27 = -1
        p_u_15:get_craft_button():set_enabled(false)
    end;
    v17.set_visible = function(_, p39) --[[ Name: set_visible ]] --[[ Line: 96 ]]
        --[[ Upvalues: (ref 1): v_u_18, (copy 2): p_u_15 ]]
        v_u_18.Visible = p39
        if p39 then
            p_u_15:get_craft_button():set_visible(true)
            p_u_15:get_craft_button():set_enabled(false)
            p_u_15:get_use_button():set_visible(false)
        end;
    end;
    v17.get_song_recipes_list = function(_) --[[ Name: get_song_recipes_list ]] --[[ Line: 105 ]]
        --[[ Upvalues: (ref 1): v_u_5, (copy 2): p_u_14, (ref 3): v_u_2, (ref 4): v_u_4, (ref 5): v_u_3, (copy 6): p_u_15, (ref 7): v_u_7, (ref 8): v_u_12 ]]
        v_u_5:profilebegin("CraftingUITabSongs:get_song_recipes_list")
        local v40 = p_u_14._player_blob_manager:get_player_blob()
        v_u_5:profilebegin("PlayerBlobCrafting:get_playerblob_craftable_song_recipe_ids_list")
        local v41 = v_u_2:get_playerblob_craftable_song_recipe_ids_list(v40, p_u_14._player_blob_manager:get_cached_collection_info())
        v_u_5:profileend()
        local v42 = v_u_4:new()
        local v43 = v_u_4:new()
        local v44 = v_u_4:new()
        for v45 = 1, v41:count() do
            local v46 = v41:get(v45)
            if v_u_2:can_craft_requirements_dict(v40, v_u_3:singleton():get_song_recipe_requirements_dict(v46)) then
                v43:push_back(v46)
            else
                v44:push_back(v46)
            end;
        end;
        local function f_sort_filter_recipe_id_list(p47) --[[ Name: sort_filter_recipe_id_list ]] --[[ Line: 128 ]]
            --[[ Upvalues: (ref 1): p_u_15, (ref 2): v_u_3, (ref 3): v_u_7, (ref 4): v_u_12 ]]
            local v_u_48 = string.lower(p_u_15:get_search_name())
            p47:remove_if(function(p49, _) --[[ Line: 130 ]]
                --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_7, (copy 3): v_u_48 ]]
                return string.find(string.lower((v_u_7:singleton():get_title_for_key((v_u_3:singleton():get_song_recipe_songkey(p49))))), v_u_48, 1, true) == nil;
            end)
            if p_u_15:get_sort_type() == v_u_12.SortType.Category1 then
                local function f_song_name_sort(p50, p51) --[[ Name: song_name_sort ]] --[[ Line: 136 ]]
                    --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_7 ]]
                    return v_u_7:singleton():get_title_for_key((v_u_3:singleton():get_song_recipe_songkey(p51))) > v_u_7:singleton():get_title_for_key((v_u_3:singleton():get_song_recipe_songkey(p50))) == false and -1 or 1;
                end;
                local function f_song_name_sort_inverse(p52, p53) --[[ Name: song_name_sort_inverse ]] --[[ Line: 143 ]]
                    --[[ Upvalues: (copy 1): f_song_name_sort ]]
                    return f_song_name_sort(p52, p53) * -1;
                end;
                if p_u_15:get_sort_order() == v_u_12.SortOrder.Ascending then
                    p47:sort(f_song_name_sort)
                else
                    p47:sort(f_song_name_sort_inverse)
                end;
            else
                if p_u_15:get_sort_type() == v_u_12.SortType.Category2 then
                    local function f_song_difficulty_sort(p54, p55) --[[ Name: song_difficulty_sort ]] --[[ Line: 153 ]]
                        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_7 ]]
                        return v_u_7:singleton():get_difficulty_for_key((v_u_3:singleton():get_song_recipe_songkey(p55))) - v_u_7:singleton():get_difficulty_for_key((v_u_3:singleton():get_song_recipe_songkey(p54)));
                    end;
                    local function f_song_difficulty_sort_inverse(p56, p57) --[[ Name: song_difficulty_sort_inverse ]] --[[ Line: 158 ]]
                        --[[ Upvalues: (copy 1): f_song_difficulty_sort ]]
                        return f_song_difficulty_sort(p56, p57) * -1;
                    end;
                    if p_u_15:get_sort_order() == v_u_12.SortOrder.Ascending then
                        p47:sort(f_song_difficulty_sort)
                        return;
                    end;
                    p47:sort(f_song_difficulty_sort_inverse)
                end;
                return;
            end;
        end;
        f_sort_filter_recipe_id_list(v43)
        f_sort_filter_recipe_id_list(v44)
        v42:push_back_from_list(v43)
        v42:push_back_from_list(v44)
        v_u_5:profileend()
        return v42;
    end;
    v17.redraw_list = function(p58) --[[ Name: redraw_list ]] --[[ Line: 179 ]]
        --[[ Upvalues: (copy 1): p_u_15, (copy 2): p_u_14, (ref 3): v_u_26, (ref 4): v_u_3, (ref 5): v_u_6, (ref 6): v_u_7, (ref 7): v_u_2 ]]
        p_u_15:clear_list()
        local v59 = p_u_14._player_blob_manager:get_player_blob()
        local v60 = p58:get_song_recipes_list()
        local v61 = p_u_15:get_list_elements()
        for v62 = 1, v61:count() do
            local v63 = v61:get(v62)
            local v64 = v_u_26 * v61:count() + v62
            if v64 <= v60:count() then
                local v65 = v60:get(v64)
                local v66 = v_u_3:singleton():get_song_recipe_songkey(v65)
                v63:set_info(v65, "", v_u_6:get_song_key_owned_count(v59, v66))
                local v67, v68 = v63:get_icon_and_overlay()
                v_u_7:singleton():render_coverimage_for_key(v67, v68, v66)
                v63:set_visible(true)
                if v_u_2:can_craft_requirements_dict(v59, v_u_3:singleton():get_song_recipe_requirements_dict(v65)) then
                    v63:set_alpha(1)
                else
                    v63:set_alpha(0.35)
                end;
            end;
        end;
    end;
    v17.page_up = function(p69) --[[ Name: page_up ]] --[[ Line: 214 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        v_u_26 = v_u_26 - 1
        p69:redraw_list()
    end;
    v17.page_down = function(p70) --[[ Name: page_down ]] --[[ Line: 219 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        v_u_26 = v_u_26 + 1
        p70:redraw_list()
    end;
    v17.can_page_up = function(_) --[[ Name: can_page_up ]] --[[ Line: 224 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        return v_u_26 > 0;
    end;
    v17.can_page_down = function(p71) --[[ Name: can_page_down ]] --[[ Line: 228 ]]
        --[[ Upvalues: (ref 1): v_u_26, (copy 2): p_u_15 ]]
        return (v_u_26 + 1) * p_u_15:get_list_elements():count() < p71:get_song_recipes_list():count();
    end;
    v17.reset_page = function(_) --[[ Name: reset_page ]] --[[ Line: 232 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        v_u_26 = 0
    end;
    v17.list_element_pressed = function(_, _, p72) --[[ Name: list_element_pressed ]] --[[ Line: 234 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_8, (ref 3): v_u_27, (copy 4): p_u_14, (ref 5): v_u_7, (ref 6): v_u_19, (ref 7): v_u_20, (ref 8): v_u_21, (ref 9): v_u_22, (ref 10): v_u_23, (ref 11): v_u_6, (ref 12): v_u_24, (copy 13): v_u_25, (ref 14): v_u_2, (copy 15): p_u_15 ]]
        if v_u_3:singleton():get_song_recipe(p72) == nil then
            v_u_8:errf("CraftingUITabSongs list_element_pressed invalid song_recipe(%s)", (tostring(p72)))
        end;
        v_u_27 = p72
        local v73 = p_u_14._player_blob_manager:get_player_blob()
        local v74 = v_u_3:singleton():get_song_recipe_songkey(v_u_27)
        v_u_7:singleton():render_coverimage_for_key(v_u_19, v_u_20, v74)
        v_u_21.Text = v_u_7:singleton():get_title_for_key(v74)
        v_u_22.Text = v_u_7:singleton():get_description_for_key(v74)
        v_u_23.Text = string.format("%d", v_u_6:get_song_key_owned_count(v73, v74))
        v_u_24.Text = string.format("%d", v_u_7:singleton():get_difficulty_for_key(v74))
        for v75 = 1, v_u_25:count() do
            v_u_25:get(v75):set_visible(false)
        end;
        local v76 = v_u_3:singleton():get_song_recipe_requirements_dict(v_u_27)
        local v77 = v76:key_list()
        for v78 = 1, v_u_25:count() do
            if v77:count() < v78 then
                break;
            end;
            local v79 = v77:get(v78)
            local v80 = v_u_25:get(v78)
            v80:set_visible(true)
            v80:set_info(v_u_3:singleton():get_material_name(v79), v_u_3:singleton():get_material_icon(v79), v_u_3:singleton():tier_get_color(v_u_3:singleton():get_material_tier(v79)), v_u_2:get_count_of_material(v73, v79), v76:get(v79))
        end;
        p_u_15:get_craft_button():set_enabled(v_u_2:can_craft_requirements_dict(v73, v76))
        if v_u_6:get_song_key_owned_count(v73, v74) > 0 then
            p_u_15:set_combine_song_info_selected_song_key(v74)
        end;
    end;
    v17.craft_pressed = function(p_u_81) --[[ Name: craft_pressed ]] --[[ Line: 278 ]]
        --[[ Upvalues: (ref 1): v_u_27, (copy 2): l__menus_0, (ref 3): v_u_9, (copy 4): p_u_14, (copy 5): l__spui_0, (ref 6): v_u_3, (copy 7): p_u_15, (ref 8): v_u_10 ]]
        if v_u_27 < 0 then
            return l__menus_0:push_menu(v_u_9:new(p_u_14, l__spui_0, l__menus_0):set_text("Failed", "No recipe selected"));
        end;
        local v_u_82 = v_u_27
        local v_u_83 = v_u_3:singleton():get_song_recipe_songkey(v_u_27)
        local v_u_84 = l__menus_0:push_menu(v_u_9:new(p_u_14, l__spui_0, l__menus_0):set_text("Crafting...", ""):set_close_button_visible(false))
        p_u_14._shop_local_protocol:try_craft_song_recipe(v_u_82, function(p85, p86) --[[ Line: 286 ]]
            --[[ Upvalues: (ref 1): l__menus_0, (copy 2): v_u_84, (ref 3): v_u_9, (ref 4): p_u_14, (ref 5): l__spui_0, (copy 6): p_u_81, (ref 7): p_u_15, (copy 8): v_u_83, (ref 9): v_u_10, (ref 10): v_u_3, (copy 11): v_u_82 ]]
            if p85 == true then
                p_u_14._player_blob_manager:do_sync(function(_) --[[ Line: 293 ]]
                    --[[ Upvalues: (ref 1): p_u_81, (ref 2): p_u_15, (ref 3): v_u_83, (ref 4): l__menus_0, (ref 5): v_u_84, (ref 6): v_u_10, (ref 7): p_u_14, (ref 8): l__spui_0, (ref 9): v_u_3, (ref 10): v_u_82 ]]
                    p_u_81:clear_selected_display()
                    p_u_15:set_on_refocus_selected_element(v_u_83)
                    l__menus_0:remove_menu(v_u_84)
                    l__menus_0:push_menu(v_u_10:new(p_u_14, l__spui_0, l__menus_0, v_u_3:singleton():get_song_recipe_songkey(v_u_82)))
                end)
            else
                l__menus_0:remove_menu(v_u_84)
                l__menus_0:push_menu(v_u_9:new(p_u_14, l__spui_0, l__menus_0):set_text("Crafting failed.", p86))
            end;
        end)
    end;
    v17.is_search_section_enabled = function(_) --[[ Name: is_search_section_enabled ]] --[[ Line: 309 ]]
        return true;
    end;
    v17.get_category_names = function(_) --[[ Name: get_category_names ]] --[[ Line: 310 ]]
        return "Name", "Difficulty";
    end;
    v17:cons()
    return v17;
end;
return v_u_13;
