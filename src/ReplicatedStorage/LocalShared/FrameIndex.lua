-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:02 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_12 = {
    ["Test"] = {
        ["CharacterCulling"] = 1,
        ["Chat"] = 2,
        ["FollowNPC"] = 3,
        ["MatchPreviewNPC"] = 4,
        ["LobbyNPCManager"] = 5,
        ["CharacterManager"] = 6,
        ["MenuVisualUpdate"] = 7,
        ["MenuBehaviourUpdate"] = 8,
        ["GamePlaceSlots"] = 9,
        ["GamePowerBar"] = 10,
        ["GameComboNotif"] = 11,
        ["GameSongMarker"] = 12,
        ["GameRankBar"] = 13,
        ["GameMissionBar"] = 14,
        ["GameQuitDisplay"] = 15
    },
    ["State"] = {
        ["new"] = function(_, p_u_14, p_u_15, p_u_16) --[[ Name: new ]] --[[ Line: 32 ]]
            --[[ Upvalues: (copy 1): v_u_1 ]]
            local v17 = {}
            local v_u_18 = 0
            local v_u_19 = v_u_1:new()
            local v_u_20 = v_u_1:new()
            v17.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 39 ]]
                --[[ Upvalues: (copy 1): p_u_16 ]]
                return p_u_16;
            end;
            v17.get_test_val = function(_) --[[ Name: get_test_val ]] --[[ Line: 40 ]]
                --[[ Upvalues: (copy 1): p_u_15 ]]
                return p_u_15;
            end;
            v17.get_dt_scale = function(_) --[[ Name: get_dt_scale ]] --[[ Line: 41 ]]
                --[[ Upvalues: (ref 1): v_u_18 ]]
                return v_u_18;
            end;
            v17.get_just_pressed_keys = function(_) --[[ Name: get_just_pressed_keys ]] --[[ Line: 42 ]]
                --[[ Upvalues: (copy 1): v_u_19 ]]
                return v_u_19;
            end;
            v17.get_just_released_keys = function(_) --[[ Name: get_just_released_keys ]] --[[ Line: 43 ]]
                --[[ Upvalues: (copy 1): v_u_20 ]]
                return v_u_20;
            end;
            v17.update = function(_, p21) --[[ Name: update ]] --[[ Line: 45 ]]
                --[[ Upvalues: (ref 1): v_u_18, (ref 2): v_u_1, (copy 3): v_u_19, (copy 4): p_u_14, (copy 5): v_u_20 ]]
                v_u_18 = v_u_18 + p21
                v_u_1:set_union(v_u_19, p_u_14._input:get_just_pressed_keys(), v_u_19)
                v_u_1:set_union(v_u_20, p_u_14._input:get_just_released_keys(), v_u_20)
            end;
            v17.post_update = function(_, _) --[[ Name: post_update ]] --[[ Line: 51 ]]
                --[[ Upvalues: (ref 1): v_u_18, (copy 2): v_u_19, (copy 3): v_u_20 ]]
                v_u_18 = 0
                v_u_19:clear()
                v_u_20:clear()
            end;
            return v17;
        end
    }
}
local v_u_13 = {
    ["CharacterCulling"] = 1,
    ["Chat"] = 2,
    ["FollowNPC"] = 3,
    ["MatchPreviewNPC"] = 4,
    ["LobbyNPCManager"] = 5,
    ["CharacterManager"] = 6,
    ["MenuVisualUpdate"] = 7,
    ["MenuBehaviourUpdate"] = 8,
    ["GamePlaceSlots"] = 9,
    ["GamePowerBar"] = 10,
    ["GameComboNotif"] = 11,
    ["GameSongMarker"] = 12,
    ["GameRankBar"] = 13,
    ["GameMissionBar"] = 14,
    ["GameQuitDisplay"] = 15
}
local v_u_22 = {
    ["new"] = function(_, p_u_14, p_u_15, p_u_16) --[[ Name: new ]] --[[ Line: 32 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        local v17 = {}
        local v_u_18 = 0
        local v_u_19 = v_u_1:new()
        local v_u_20 = v_u_1:new()
        v17.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 39 ]]
            --[[ Upvalues: (copy 1): p_u_16 ]]
            return p_u_16;
        end;
        v17.get_test_val = function(_) --[[ Name: get_test_val ]] --[[ Line: 40 ]]
            --[[ Upvalues: (copy 1): p_u_15 ]]
            return p_u_15;
        end;
        v17.get_dt_scale = function(_) --[[ Name: get_dt_scale ]] --[[ Line: 41 ]]
            --[[ Upvalues: (ref 1): v_u_18 ]]
            return v_u_18;
        end;
        v17.get_just_pressed_keys = function(_) --[[ Name: get_just_pressed_keys ]] --[[ Line: 42 ]]
            --[[ Upvalues: (copy 1): v_u_19 ]]
            return v_u_19;
        end;
        v17.get_just_released_keys = function(_) --[[ Name: get_just_released_keys ]] --[[ Line: 43 ]]
            --[[ Upvalues: (copy 1): v_u_20 ]]
            return v_u_20;
        end;
        v17.update = function(_, p21) --[[ Name: update ]] --[[ Line: 45 ]]
            --[[ Upvalues: (ref 1): v_u_18, (ref 2): v_u_1, (copy 3): v_u_19, (copy 4): p_u_14, (copy 5): v_u_20 ]]
            v_u_18 = v_u_18 + p21
            v_u_1:set_union(v_u_19, p_u_14._input:get_just_pressed_keys(), v_u_19)
            v_u_1:set_union(v_u_20, p_u_14._input:get_just_released_keys(), v_u_20)
        end;
        v17.post_update = function(_, _) --[[ Name: post_update ]] --[[ Line: 51 ]]
            --[[ Upvalues: (ref 1): v_u_18, (copy 2): v_u_19, (copy 3): v_u_20 ]]
            v_u_18 = 0
            v_u_19:clear()
            v_u_20:clear()
        end;
        return v17;
    end
}
local v_u_23 = v_u_1:new()
v_u_12.register_ui_needs_refresh_should_run_test_type = function(_, p24) --[[ Name: register_ui_needs_refresh_should_run_test_type ]] --[[ Line: 61 ]]
    --[[ Upvalues: (copy 1): v_u_23 ]]
    v_u_23:add_set(p24)
end;
v_u_12.new = function(_, p_u_25) --[[ Name: new ]] --[[ Line: 65 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_13, (copy 3): v_u_22, (copy 4): v_u_3, (copy 5): v_u_23, (copy 6): v_u_2, (copy 7): v_u_12 ]]
    local v26 = {}
    local v_u_27 = 1
    local v_u_28 = v_u_1:new()
    local v_u_29 = CFrame.new()
    local v_u_30 = Vector3.new(-1, -1, -1)
    local v_u_31 = false
    local function f_cons() --[[ Name: cons ]] --[[ Line: 74 ]]
        --[[ Upvalues: (ref 1): v_u_13, (copy 2): v_u_28, (ref 3): v_u_22, (copy 4): p_u_25 ]]
        for v32, v33 in pairs(v_u_13) do
            v_u_28:add(v33, v_u_22:new(p_u_25, v33, v32))
        end;
    end;
    v26.get_index = function(_) --[[ Name: get_index ]] --[[ Line: 80 ]]
        --[[ Upvalues: (ref 1): v_u_27 ]]
        return v_u_27;
    end;
    v26.get_next_index = function(_) --[[ Name: get_next_index ]] --[[ Line: 81 ]]
        --[[ Upvalues: (ref 1): v_u_27 ]]
        local v34 = v_u_27 + 1
        return v34 > 72 and 1 or v34;
    end;
    v26.update = function(p35, p36) --[[ Name: update ]] --[[ Line: 89 ]]
        --[[ Upvalues: (ref 1): v_u_27, (copy 2): v_u_28 ]]
        v_u_27 = p35:get_next_index()
        for _, v37 in v_u_28:key_itr() do
            v37:update(p36)
        end;
    end;
    v26.update_post_camera_moved = function(_, _) --[[ Name: update_post_camera_moved ]] --[[ Line: 96 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_31, (ref 3): v_u_29, (ref 4): v_u_30 ]]
        local v38 = v_u_3:get_camera_cframe_uncached()
        v_u_31 = v38 ~= v_u_29 and true or v_u_30 ~= v_u_3:screen_size()
        v_u_30 = v_u_3:screen_size()
        v_u_29 = v38
    end;
    v26.post_update = function(p39, p40) --[[ Name: post_update ]] --[[ Line: 104 ]]
        --[[ Upvalues: (copy 1): v_u_28, (ref 2): v_u_31, (ref 3): v_u_23, (copy 4): p_u_25, (ref 5): v_u_3, (ref 6): v_u_2 ]]
        for v41, v42 in v_u_28:key_itr() do
            if p39:should_run(v41) == true then
                v42:post_update(p40)
            elseif v_u_31 and v_u_23:contains(v41) then
                v42:post_update(p40)
            end;
        end;
        if p_u_25._input:get_frame_index_state() ~= nil then
            if v_u_3:is_dev_build() then
                v_u_2:warnf("FrameIndex:post_update input:get_frame_index_state is set, missing matching unset")
            end;
            p_u_25._input:set_frame_index_state(nil)
        end;
    end;
    v26.ui_needs_refresh = function(_) --[[ Name: ui_needs_refresh ]] --[[ Line: 121 ]]
        --[[ Upvalues: (ref 1): v_u_31 ]]
        return v_u_31;
    end;
    v26.should_run = function(_, p43) --[[ Name: should_run ]] --[[ Line: 123 ]]
        --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_27, (ref 3): v_u_31, (ref 4): v_u_23 ]]
        local v44 = not v_u_12:test_frame_index_should_run(p43, v_u_27) and v_u_31
        if v44 then
            v44 = v_u_23:contains(p43)
        end;
        return v44;
    end;
    v26.get_test_state = function(_, p45) --[[ Name: get_test_state ]] --[[ Line: 127 ]]
        --[[ Upvalues: (copy 1): v_u_28, (ref 2): v_u_13 ]]
        local v46 = v_u_28:get(p45)
        if v46 == nil then
            v46 = v_u_28:get(v_u_13.CharacterCulling)
        end;
        return v46;
    end;
    f_cons()
    return v26;
end;
v_u_12.test_frame_index_should_run = function(_, p47, p48) --[[ Name: test_frame_index_should_run ]] --[[ Line: 139 ]]
    --[[ Upvalues: (copy 1): v_u_13 ]]
    if p47 == v_u_13.CharacterCulling then
        return (p48 + 0) % 3 == 0;
    elseif p47 == v_u_13.Chat then
        return (p48 + 0) % 3 == 0;
    elseif p47 == v_u_13.FollowNPC then
        return (p48 + 1) % 3 == 0;
    elseif p47 == v_u_13.MatchPreviewNPC then
        return (p48 + 2) % 3 == 0;
    elseif p47 == v_u_13.LobbyNPCManager then
        return (p48 + 1) % 3 == 0;
    elseif p47 == v_u_13.CharacterManager then
        return (p48 + 2) % 3 == 0;
    elseif p47 == v_u_13.MenuVisualUpdate then
        return (p48 + 0) % 2 == 0;
    elseif p47 == v_u_13.MenuBehaviourUpdate then
        return (p48 + 1) % 2 == 0;
    elseif p47 == v_u_13.GamePlaceSlots then
        return (p48 + 0) % 2 == 0;
    elseif p47 == v_u_13.GameComboNotif then
        return (p48 + 1) % 2 == 0;
    elseif p47 == v_u_13.GamePowerBar then
        return (p48 + 0) % 4 == 0;
    elseif p47 == v_u_13.GameSongMarker then
        return (p48 + 1) % 4 == 0;
    elseif p47 == v_u_13.GameRankBar then
        return (p48 + 2) % 3 == 0;
    elseif p47 == v_u_13.GameMissionBar then
        return (p48 + 3) % 4 == 0;
    else
        return p47 ~= v_u_13.GameQuitDisplay and true or (p48 + 4) % 3 == 0;
    end;
end;
local v_u_49 = nil
v_u_12.init_singleton = function(_, p50) --[[ Name: init_singleton ]] --[[ Line: 191 ]]
    --[[ Upvalues: (ref 1): v_u_49, (copy 2): v_u_12 ]]
    v_u_49 = v_u_12:new(p50)
end;
v_u_12.singleton = function(_) --[[ Name: singleton ]] --[[ Line: 195 ]]
    --[[ Upvalues: (ref 1): v_u_49 ]]
    return v_u_49;
end;
return v_u_12;
