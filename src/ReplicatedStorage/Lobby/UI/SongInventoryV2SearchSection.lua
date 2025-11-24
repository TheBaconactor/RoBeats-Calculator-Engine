-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:51 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_3 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Menu.MenuSystem)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_4 = require(game.ReplicatedStorage.Lobby.UI.SPUITextInput)
require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_5 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_6 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_7 = {
    ["SortType"] = {
        ["Difficulty"] = 1,
        ["Count"] = 2
    },
    ["SortOrder"] = {
        ["Ascending"] = 1,
        ["Descending"] = 2
    }
}
local v_u_8 = ""
local l_Difficulty_0 = v_u_7.SortType.Difficulty
local l_Ascending_0 = v_u_7.SortOrder.Ascending
v_u_7.new = function(_, p_u_9, p_u_10, _, p_u_11, p_u_12) --[[ Name: new ]] --[[ Line: 31 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_3, (copy 3): v_u_6, (ref 4): l_Difficulty_0, (copy 5): v_u_7, (ref 6): l_Ascending_0, (copy 7): v_u_4, (ref 8): v_u_8, (copy 9): v_u_1, (copy 10): v_u_5 ]]
    local v13 = {}
    local v_u_14 = nil
    local v_u_15 = nil
    local v_u_16 = false
    local v_u_17 = nil
    local v_u_18 = nil
    local v_u_19 = nil
    local v_u_20 = nil
    v13.cons = function(p_u_21) --[[ Name: cons ]] --[[ Line: 43 ]]
        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_2, (copy 3): p_u_11, (copy 4): p_u_12, (copy 5): p_u_9, (ref 6): v_u_3, (copy 7): p_u_10, (ref 8): v_u_6, (ref 9): v_u_15, (ref 10): l_Difficulty_0, (ref 11): v_u_7, (ref 12): l_Ascending_0, (ref 13): v_u_16, (ref 14): v_u_17, (ref 15): v_u_18, (ref 16): v_u_19, (ref 17): v_u_20, (ref 18): v_u_4, (ref 19): v_u_8 ]]
        v_u_14 = v_u_2:new(p_u_11, p_u_12.PrimaryPart, p_u_12.SearchSurface)
        v_u_14:set_sgui(p_u_12.SearchSurface.SurfaceGui)
        p_u_11:add_cycle_element(p_u_9, 1, v_u_3:new(v_u_2:new(v_u_14, p_u_12.PrimaryPart, p_u_12.SearchResetButton), p_u_10, function() --[[ Line: 50 ]]
            --[[ Upvalues: (ref 1): p_u_9, (ref 2): v_u_6, (ref 3): v_u_15, (ref 4): l_Difficulty_0, (ref 5): v_u_7, (ref 6): l_Ascending_0, (ref 7): v_u_16, (copy 8): p_u_21 ]]
            p_u_9._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
            v_u_15:set_text("")
            l_Difficulty_0 = v_u_7.SortType.Difficulty
            l_Ascending_0 = v_u_7.SortOrder.Ascending
            v_u_16 = true
            p_u_21:update_sorttype_visual()
            p_u_21:update_sortorder_visual()
        end))
        v_u_17 = p_u_11:add_cycle_element(p_u_9, 1, v_u_3:new(v_u_2:new(v_u_14, p_u_12.PrimaryPart, p_u_12.SortDifficultyButton), p_u_10, function() --[[ Line: 64 ]]
            --[[ Upvalues: (ref 1): p_u_9, (ref 2): v_u_6, (ref 3): l_Difficulty_0, (ref 4): v_u_7, (ref 5): v_u_16, (copy 6): p_u_21 ]]
            p_u_9._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
            l_Difficulty_0 = v_u_7.SortType.Difficulty
            v_u_16 = true
            p_u_21:update_sorttype_visual()
        end))
        v_u_18 = p_u_11:add_cycle_element(p_u_9, 1, v_u_3:new(v_u_2:new(v_u_14, p_u_12.PrimaryPart, p_u_12.SortCountButton), p_u_10, function() --[[ Line: 75 ]]
            --[[ Upvalues: (ref 1): p_u_9, (ref 2): v_u_6, (ref 3): l_Difficulty_0, (ref 4): v_u_7, (ref 5): v_u_16, (copy 6): p_u_21 ]]
            p_u_9._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
            l_Difficulty_0 = v_u_7.SortType.Count
            v_u_16 = true
            p_u_21:update_sorttype_visual()
        end))
        v_u_19 = p_u_11:add_cycle_element(p_u_9, 1, v_u_3:new(v_u_2:new(v_u_14, p_u_12.PrimaryPart, p_u_12.SortAscendingButton), p_u_10, function() --[[ Line: 86 ]]
            --[[ Upvalues: (ref 1): p_u_9, (ref 2): v_u_6, (ref 3): l_Ascending_0, (ref 4): v_u_7, (ref 5): v_u_16, (copy 6): p_u_21 ]]
            p_u_9._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
            l_Ascending_0 = v_u_7.SortOrder.Ascending
            v_u_16 = true
            p_u_21:update_sortorder_visual()
        end))
        v_u_20 = p_u_11:add_cycle_element(p_u_9, 1, v_u_3:new(v_u_2:new(v_u_14, p_u_12.PrimaryPart, p_u_12.SortDescendingButton), p_u_10, function() --[[ Line: 97 ]]
            --[[ Upvalues: (ref 1): p_u_9, (ref 2): v_u_6, (ref 3): l_Ascending_0, (ref 4): v_u_7, (ref 5): v_u_16, (copy 6): p_u_21 ]]
            p_u_9._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
            l_Ascending_0 = v_u_7.SortOrder.Descending
            v_u_16 = true
            p_u_21:update_sortorder_visual()
        end))
        p_u_21:update_sorttype_visual()
        p_u_21:update_sortorder_visual()
        v_u_15 = v_u_4:new(p_u_9, p_u_12.SearchSurface.SurfaceGui.Frame.NameInput.TextLabel, nil, v_u_14, p_u_10):set_empty_message("Type in name to search here."):set_send_behaviour_enabled(false):set_max_length(23)
        v_u_15:set_text(v_u_8)
        p_u_21:raise_changed()
    end;
    local function f_set_image_children_alpha(p22, p23) --[[ Name: set_image_children_alpha ]] --[[ Line: 123 ]]
        --[[ Upvalues: (ref 1): v_u_1 ]]
        local v24 = v_u_1:get_list_of_children_of_classname(p22, "ImageLabel")
        for v25 = 1, v24:count() do
            local v26 = v24:get(v25)
            v26.Name = v_u_1:r_set_alpha_generate_name({
                ["ImageAlpha"] = p23
            }, "ImageLabel")
            v26.ImageTransparency = v_u_1:tra(p23)
        end;
    end;
    v13.update_sorttype_visual = function(_) --[[ Name: update_sorttype_visual ]] --[[ Line: 132 ]]
        --[[ Upvalues: (ref 1): l_Difficulty_0, (ref 2): v_u_7, (ref 3): v_u_17, (ref 4): v_u_18, (copy 5): f_set_image_children_alpha ]]
        local v27, v28
        if l_Difficulty_0 == v_u_7.SortType.Difficulty then
            v_u_17:set_scale(1)
            v_u_18:set_scale(0.8)
            v27 = 1
            v28 = 0.2
        else
            v_u_17:set_scale(0.8)
            v_u_18:set_scale(1)
            v27 = 0.2
            v28 = 1
        end;
        f_set_image_children_alpha(v_u_17:get_part(), v27)
        f_set_image_children_alpha(v_u_18:get_part(), v28)
    end;
    v13.update_sortorder_visual = function(_) --[[ Name: update_sortorder_visual ]] --[[ Line: 150 ]]
        --[[ Upvalues: (ref 1): l_Ascending_0, (ref 2): v_u_7, (ref 3): v_u_19, (ref 4): v_u_20, (copy 5): f_set_image_children_alpha ]]
        local v29, v30
        if l_Ascending_0 == v_u_7.SortOrder.Ascending then
            v_u_19:set_scale(1)
            v_u_20:set_scale(0.8)
            v29 = 1
            v30 = 0.2
        else
            v_u_19:set_scale(0.8)
            v_u_20:set_scale(1)
            v29 = 0.2
            v30 = 1
        end;
        f_set_image_children_alpha(v_u_19:get_part(), v29)
        f_set_image_children_alpha(v_u_20:get_part(), v30)
    end;
    v13.layout = function(_) --[[ Name: layout ]] --[[ Line: 168 ]]
        --[[ Upvalues: (ref 1): v_u_14 ]]
        v_u_14:layout()
    end;
    v13.behaviour_update = function(_, p31, _) --[[ Name: behaviour_update ]] --[[ Line: 172 ]]
        --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_8 ]]
        v_u_15:update(p31)
        v_u_8 = v_u_15:get_current_text()
    end;
    v13.cleanup = function(_) --[[ Name: cleanup ]] --[[ Line: 177 ]]
        --[[ Upvalues: (ref 1): v_u_15 ]]
        v_u_15:cleanup()
    end;
    v13.get_search_name = function(_) --[[ Name: get_search_name ]] --[[ Line: 181 ]]
        --[[ Upvalues: (ref 1): v_u_15 ]]
        return v_u_15:get_current_text();
    end;
    v13.get_sort_fnkey = function(_) --[[ Name: get_sort_fnkey ]] --[[ Line: 185 ]]
        --[[ Upvalues: (ref 1): l_Difficulty_0, (ref 2): v_u_7, (ref 3): l_Ascending_0, (ref 4): v_u_5 ]]
        if l_Difficulty_0 == v_u_7.SortType.Difficulty then
            if l_Ascending_0 == v_u_7.SortOrder.Ascending then
                return v_u_5.SongInventorySort_DifficultyAsc;
            else
                return v_u_5.SongInventorySort_DifficultyDesc;
            end;
        elseif l_Ascending_0 == v_u_7.SortOrder.Ascending then
            return v_u_5.SongInventorySort_OwnedCountAsc;
        else
            return v_u_5.SongInventorySort_OwnedCountDesc;
        end;
    end;
    v13.raise_changed = function(_) --[[ Name: raise_changed ]] --[[ Line: 201 ]]
        --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_15 ]]
        local v32 = v_u_16
        v_u_16 = false
        local v33 = v_u_15:raise_changed()
        return v32 or v33, v32, v33;
    end;
    v13:cons()
    return v13;
end;
return v_u_7;
