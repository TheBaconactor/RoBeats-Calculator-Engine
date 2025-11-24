-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:51 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Menu.MenuSystem)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_6 = require(game.ReplicatedStorage.Lobby.UI.SPUITextInput)
require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_7 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_8 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
local v_u_9 = require(game.ReplicatedStorage.Crafting.ColorTierMaterial)
local v_u_10 = require(game.ReplicatedStorage.PlayerInfo.BoxInfo)
local v_u_11 = require(game.ReplicatedStorage.Crafting.CraftingMaterialBase)
local v12 = require(game.ReplicatedStorage.Avatar.EquipmentUpgradeDatabase)
local v_u_13 = {
    ["SortType"] = {
        ["Category1"] = 1,
        ["Category2"] = 2
    },
    ["SortOrder"] = {
        ["Ascending"] = 1,
        ["Descending"] = 2
    }
}
v_u_13.new = function(_, p_u_14, p_u_15, _, p_u_16, p_u_17, p_u_18) --[[ Name: new ]] --[[ Line: 32 ]]
    --[[ Upvalues: (copy 1): v_u_13, (copy 2): v_u_3, (copy 3): v_u_4, (copy 4): v_u_5, (copy 5): v_u_7, (copy 6): v_u_6, (copy 7): v_u_1 ]]
    local v19 = {}
    local v_u_20 = nil
    local v_u_21 = nil
    local v_u_22 = false
    local v_u_23 = ""
    local l_Category1_0 = v_u_13.SortType.Category1
    local l_Ascending_0 = v_u_13.SortOrder.Ascending
    local v_u_24 = nil
    local v_u_25 = nil
    local v_u_26 = nil
    local v_u_27 = nil
    local v_u_28 = v_u_3:new()
    local v_u_29 = false
    v19.set_enabled = function(_, p30) --[[ Name: set_enabled ]] --[[ Line: 51 ]]
        --[[ Upvalues: (ref 1): v_u_29, (copy 2): v_u_28, (ref 3): v_u_20 ]]
        v_u_29 = p30
        for v31 = 1, v_u_28:count() do
            v_u_28:get(v31):set_visible(v_u_29)
        end;
        v_u_20:set_visible(v_u_29)
    end;
    local v_u_32 = nil
    local v_u_33 = nil
    v19.set_category_names = function(_, p34, p35) --[[ Name: set_category_names ]] --[[ Line: 62 ]]
        --[[ Upvalues: (ref 1): v_u_32, (ref 2): v_u_33 ]]
        v_u_32.Text = p34
        v_u_33.Text = p35
    end;
    v19.reset = function(p36) --[[ Name: reset ]] --[[ Line: 67 ]]
        --[[ Upvalues: (ref 1): v_u_21, (ref 2): l_Category1_0, (ref 3): v_u_13, (ref 4): l_Ascending_0, (ref 5): v_u_22 ]]
        v_u_21:set_text("")
        l_Category1_0 = v_u_13.SortType.Category1
        l_Ascending_0 = v_u_13.SortOrder.Ascending
        v_u_22 = true
        p36:update_sorttype_visual()
        p36:update_sortorder_visual()
    end;
    v19.cons = function(p_u_37) --[[ Name: cons ]] --[[ Line: 76 ]]
        --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_4, (copy 3): p_u_16, (copy 4): p_u_17, (copy 5): p_u_18, (ref 6): v_u_32, (ref 7): v_u_33, (copy 8): p_u_14, (ref 9): v_u_5, (copy 10): p_u_15, (ref 11): v_u_7, (copy 12): v_u_28, (ref 13): v_u_24, (ref 14): l_Category1_0, (ref 15): v_u_13, (ref 16): v_u_22, (ref 17): v_u_25, (ref 18): v_u_26, (ref 19): l_Ascending_0, (ref 20): v_u_27, (ref 21): v_u_21, (ref 22): v_u_6, (ref 23): v_u_23 ]]
        v_u_20 = v_u_4:new(p_u_16, p_u_17, p_u_18)
        v_u_20:set_sgui(p_u_18.SurfaceGui)
        v_u_32 = p_u_18.SortCategory1Button.SurfaceGui.Frame.TextLabel
        v_u_33 = p_u_18.SortCategory2Button.SurfaceGui.Frame.TextLabel
        v_u_28:push_back((p_u_16:add_cycle_element(p_u_14, 1, v_u_5:new(v_u_4:new(v_u_20, p_u_17, p_u_18.SearchResetButton), p_u_15, function() --[[ Line: 86 ]]
            --[[ Upvalues: (ref 1): p_u_14, (ref 2): v_u_7, (copy 3): p_u_37 ]]
            p_u_14._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            p_u_37:reset()
        end))))
        v_u_24 = p_u_16:add_cycle_element(p_u_14, 1, v_u_5:new(v_u_4:new(v_u_20, p_u_17, p_u_18.SortCategory1Button), p_u_15, function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): p_u_14, (ref 2): v_u_7, (ref 3): l_Category1_0, (ref 4): v_u_13, (ref 5): v_u_22, (copy 6): p_u_37 ]]
            p_u_14._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            l_Category1_0 = v_u_13.SortType.Category1
            v_u_22 = true
            p_u_37:update_sorttype_visual()
        end))
        v_u_28:push_back(v_u_24)
        v_u_25 = p_u_16:add_cycle_element(p_u_14, 1, v_u_5:new(v_u_4:new(v_u_20, p_u_17, p_u_18.SortCategory2Button), p_u_15, function() --[[ Line: 108 ]]
            --[[ Upvalues: (ref 1): p_u_14, (ref 2): v_u_7, (ref 3): l_Category1_0, (ref 4): v_u_13, (ref 5): v_u_22, (copy 6): p_u_37 ]]
            p_u_14._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            l_Category1_0 = v_u_13.SortType.Category2
            v_u_22 = true
            p_u_37:update_sorttype_visual()
        end))
        v_u_28:push_back(v_u_25)
        v_u_26 = p_u_16:add_cycle_element(p_u_14, 1, v_u_5:new(v_u_4:new(v_u_20, p_u_17, p_u_18.SortAscendingButton), p_u_15, function() --[[ Line: 120 ]]
            --[[ Upvalues: (ref 1): p_u_14, (ref 2): v_u_7, (ref 3): l_Ascending_0, (ref 4): v_u_13, (ref 5): v_u_22, (copy 6): p_u_37 ]]
            p_u_14._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            l_Ascending_0 = v_u_13.SortOrder.Ascending
            v_u_22 = true
            p_u_37:update_sortorder_visual()
        end))
        v_u_28:push_back(v_u_26)
        v_u_27 = p_u_16:add_cycle_element(p_u_14, 1, v_u_5:new(v_u_4:new(v_u_20, p_u_17, p_u_18.SortDescendingButton), p_u_15, function() --[[ Line: 132 ]]
            --[[ Upvalues: (ref 1): p_u_14, (ref 2): v_u_7, (ref 3): l_Ascending_0, (ref 4): v_u_13, (ref 5): v_u_22, (copy 6): p_u_37 ]]
            p_u_14._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            l_Ascending_0 = v_u_13.SortOrder.Descending
            v_u_22 = true
            p_u_37:update_sortorder_visual()
        end))
        v_u_28:push_back(v_u_27)
        p_u_37:update_sorttype_visual()
        p_u_37:update_sortorder_visual()
        v_u_21 = v_u_6:new(p_u_14, p_u_18.SurfaceGui.Frame.NameInput.TextLabel, nil, v_u_20, p_u_15):set_empty_message("Type in name to search here."):set_send_behaviour_enabled(false):set_max_length(23)
        v_u_21:set_text(v_u_23)
        p_u_37:raise_changed()
    end;
    local function f_set_image_children_alpha(p38, p39) --[[ Name: set_image_children_alpha ]] --[[ Line: 159 ]]
        --[[ Upvalues: (ref 1): v_u_1 ]]
        local v40 = v_u_1:get_list_of_children_of_classname(p38, "ImageLabel")
        for v41 = 1, v40:count() do
            local v42 = v40:get(v41)
            v42.Name = v_u_1:r_set_alpha_generate_name({
                ["ImageAlpha"] = p39
            }, "ImageLabel")
            v42.ImageTransparency = v_u_1:tra(p39)
        end;
    end;
    v19.update_sorttype_visual = function(_) --[[ Name: update_sorttype_visual ]] --[[ Line: 168 ]]
        --[[ Upvalues: (ref 1): l_Category1_0, (ref 2): v_u_13, (ref 3): v_u_24, (ref 4): v_u_25, (copy 5): f_set_image_children_alpha ]]
        local v43, v44
        if l_Category1_0 == v_u_13.SortType.Category1 then
            v_u_24:set_scale(1)
            v_u_25:set_scale(0.8)
            v43 = 1
            v44 = 0.2
        else
            v_u_24:set_scale(0.8)
            v_u_25:set_scale(1)
            v43 = 0.2
            v44 = 1
        end;
        f_set_image_children_alpha(v_u_24:get_part(), v43)
        f_set_image_children_alpha(v_u_25:get_part(), v44)
    end;
    v19.update_sortorder_visual = function(_) --[[ Name: update_sortorder_visual ]] --[[ Line: 186 ]]
        --[[ Upvalues: (ref 1): l_Ascending_0, (ref 2): v_u_13, (ref 3): v_u_26, (ref 4): v_u_27, (copy 5): f_set_image_children_alpha ]]
        local v45, v46
        if l_Ascending_0 == v_u_13.SortOrder.Ascending then
            v_u_26:set_scale(1)
            v_u_27:set_scale(0.8)
            v45 = 1
            v46 = 0.2
        else
            v_u_26:set_scale(0.8)
            v_u_27:set_scale(1)
            v45 = 0.2
            v46 = 1
        end;
        f_set_image_children_alpha(v_u_26:get_part(), v45)
        f_set_image_children_alpha(v_u_27:get_part(), v46)
    end;
    v19.layout = function(_) --[[ Name: layout ]] --[[ Line: 204 ]]
        --[[ Upvalues: (ref 1): v_u_20 ]]
        v_u_20:layout()
    end;
    v19.behaviour_update = function(_, p47, _) --[[ Name: behaviour_update ]] --[[ Line: 208 ]]
        --[[ Upvalues: (ref 1): v_u_29, (ref 2): v_u_21, (ref 3): v_u_23 ]]
        if v_u_29 == true then
            v_u_21:update(p47)
            v_u_23 = v_u_21:get_current_text()
        end;
    end;
    v19.cleanup = function(_) --[[ Name: cleanup ]] --[[ Line: 214 ]]
        --[[ Upvalues: (ref 1): v_u_21 ]]
        v_u_21:cleanup()
    end;
    v19.get_search_name = function(_) --[[ Name: get_search_name ]] --[[ Line: 218 ]]
        --[[ Upvalues: (ref 1): v_u_21 ]]
        return v_u_21:get_current_text();
    end;
    v19.get_sort_type = function(_) --[[ Name: get_sort_type ]] --[[ Line: 222 ]]
        --[[ Upvalues: (ref 1): l_Category1_0 ]]
        return l_Category1_0;
    end;
    v19.get_sort_order = function(_) --[[ Name: get_sort_order ]] --[[ Line: 226 ]]
        --[[ Upvalues: (ref 1): l_Ascending_0 ]]
        return l_Ascending_0;
    end;
    v19.raise_changed = function(_) --[[ Name: raise_changed ]] --[[ Line: 230 ]]
        --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_21 ]]
        local v48 = v_u_22
        v_u_22 = false
        return v48 or v_u_21:raise_changed();
    end;
    v19:cons()
    return v19;
end;
local v_u_49 = v2:new({
    [v12:singleton():get_upgrade_boost_untradeable_material_id()] = 3001,
    [v12:singleton():get_upgrade_boost_material_id()] = 3002,
    [v12:singleton():get_upgrade_protect_untradeable_material_id()] = 3003,
    [v12:singleton():get_upgrade_protect_material_id()] = 3004,
    [v12:singleton():get_upgrade_cleaner_material_id()] = 3005
})
v_u_13.materialid_get_type_sort_value = function(_, p50) --[[ Name: materialid_get_type_sort_value ]] --[[ Line: 249 ]]
    --[[ Upvalues: (copy 1): v_u_8, (copy 2): v_u_49, (copy 3): v_u_9, (copy 4): v_u_10, (copy 5): v_u_11 ]]
    local v51 = v_u_8:singleton():get_material(p50)
    if v_u_49:contains(p50) then
        return v_u_49:get(p50);
    elseif v_u_9:get_color_and_tier_for_material_id(p50) == nil then
        if v51:is_box() then
            local v52 = v_u_10:get_materialid_box_type(p50)
            return (v52 == v_u_11.BoxType.SmallNote and 0 or (v52 == v_u_11.BoxType.MediumNote and 100 or (v52 == v_u_11.BoxType.LargeNote and 200 or (v52 == v_u_11.BoxType.Gem and 300 or (v52 == v_u_11.BoxType.MiniOneStar and 500 or (v52 == v_u_11.BoxType.MiniTwoStar and 600 or (v52 == v_u_11.BoxType.VIPSongNormal and 700 or (v52 == v_u_11.BoxType.VIPSongHard and 800 or (v52 == v_u_11.BoxType.Token and 400 or 900))))))))) + (v51:is_tradeable() == false and 0 or 5);
        elseif v51:is_leaderboard_ticket() then
            return 1000;
        elseif v51:is_pet() then
            return 4000 + p50;
        elseif v51:is_blueprint() then
            return 5000 + p50;
        elseif v51:is_fever_icon() then
            return 6000 + p50;
        else
            return 3000 + p50;
        end;
    else
        local v53 = v_u_9:get_color_and_tier_for_material_id(p50)
        return 2000 + v53:get(2) * 10 + v53:get(1);
    end;
end;
return v_u_13;
