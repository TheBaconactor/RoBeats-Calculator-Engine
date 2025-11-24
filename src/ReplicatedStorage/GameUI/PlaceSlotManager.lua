-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:29 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_4 = require(game.ReplicatedStorage.GameUI.PlayerPlaceSlot)
require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Shared.EventString)
local v_u_5 = require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_6 = require(game.ReplicatedStorage.LocalShared.FrameIndex)
local v7 = {}
local function v_u_10(p8, p9) --[[ Line: 14 ]]
    return p8._score - p9._score;
end;
local function v_u_13(p11, p12) --[[ Line: 17 ]]
    return p11._naked_score - p12._naked_score;
end;
v7.new = function(_, p_u_14) --[[ Name: new ]] --[[ Line: 21 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_4, (copy 3): v_u_1, (copy 4): v_u_2, (copy 5): v_u_6, (copy 6): v_u_5, (copy 7): v_u_10, (copy 8): v_u_13 ]]
    local v_u_17 = {
        ["_slots"] = v_u_3:new(),
        ["teardown"] = function(p15) --[[ Name: teardown ]] --[[ Line: 36 ]]
            for v16 = 1, p15._slots:count() do
                p15._slots:get(v16):teardown()
            end;
        end
    }
    local function f_cons() --[[ Name: cons ]] --[[ Line: 26 ]]
        --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_14, (copy 3): v_u_17 ]]
        for v18 = 1, 4 do
            local v19 = v_u_4:new(p_u_14, v18)
            v19:set_enabled(false)
            v_u_17._slots:push_back(v19)
        end;
        v_u_17:layout(0, true)
    end;
    local v_u_20 = {
        ["X"] = 0.04,
        ["Y"] = 0.275
    }
    if p_u_14:show_fullscreen_mobile_ui() then
        local _, v21 = v_u_1:nontopbar_screen_pos_to_nxy(0, 0)
        v_u_20.Y = v21 + 0.05
    end;
    v_u_17.layout = function(p22, p23, p24) --[[ Name: layout ]] --[[ Line: 50 ]]
        --[[ Upvalues: (copy 1): v_u_20, (copy 2): p_u_14, (ref 3): v_u_2 ]]
        for v25 = 1, 4 do
            local v26 = p22._slots:get(v25)
            local v27 = v26:get_place()
            if v27 ~= -1 then
                v26._position_nxy.X = v_u_20.X
                local l_Y_0 = v_u_20.Y
                for v28 = 1, v27 - 1 do
                    l_Y_0 = l_Y_0 + p_u_14._spui:uiobj_get_size_nxy(p22._slots:get(v28)).Y + 0.015
                end;
                if p24 then
                    v26._position_nxy.Y = l_Y_0
                else
                    v26._position_nxy.Y = v_u_2:Expt(v26._position_nxy.Y, l_Y_0, v_u_2:NormalizedDefaultExptValueInSeconds(0.45), p23)
                end;
            end;
        end;
        for v29 = 1, 4 do
            p22._slots:get(v29):layout()
        end;
    end;
    local l_GamePlaceSlots_0 = v_u_6.Test.GamePlaceSlots
    v_u_6:register_ui_needs_refresh_should_run_test_type(l_GamePlaceSlots_0)
    v_u_17.update = function(p30, _, _) --[[ Name: update ]] --[[ Line: 94 ]]
        --[[ Upvalues: (ref 1): v_u_6, (copy 2): l_GamePlaceSlots_0, (copy 3): p_u_14 ]]
        local v31 = v_u_6:singleton()
        if v31:should_run(l_GamePlaceSlots_0) ~= false then
            local v32 = v31:get_test_state(l_GamePlaceSlots_0)
            local v33 = v32:get_dt_scale()
            p_u_14._input:set_frame_index_state(v32)
            p30:update_from_local_players(p_u_14)
            for v34 = 1, 4 do
                local v35 = p30._slots:get(v34)
                if p_u_14:es_gamelocal_get_audiomanager():is_prestart() or p_u_14:es_gamelocal_get_audiomanager():is_playing() == true then
                    v35:set_tar_alpha(1)
                else
                    v35:set_tar_alpha(0)
                end;
                v35:update(v33, p_u_14)
            end;
            p30:layout(v33, false)
            p_u_14._input:set_frame_index_state(nil)
        end;
    end;
    local v_u_36 = v_u_3:new()
    local function f___idcmpfn(p37, p38) --[[ Name: __idcmpfn ]] --[[ Line: 131 ]]
        return p37._id == p38;
    end;
    v_u_17.update_from_local_players = function(p39, _) --[[ Name: update_from_local_players ]] --[[ Line: 134 ]]
        --[[ Upvalues: (copy 1): p_u_14, (copy 2): v_u_36, (ref 3): v_u_5, (ref 4): v_u_10, (ref 5): v_u_13, (copy 6): f___idcmpfn ]]
        local l__slots_0 = p_u_14._players._slots
        v_u_36:clear()
        for _, v40 in l__slots_0:key_itr() do
            v_u_36:push_back(v40)
        end;
        if v_u_5:get_selected_mode() == v_u_5.Compete then
            v_u_36:sort(v_u_10)
        else
            v_u_36:sort(v_u_13)
        end;
        for v41 = 1, 4 do
            local v42 = p39._slots:get(v41)
            if l__slots_0:contains(v41) then
                local v43 = l__slots_0:get(v41)
                local v44 = v_u_36:find(v43._id, f___idcmpfn)
                v42:set_enabled(true)
                v42:update_player_info(v43, v41, v44)
            else
                v42:set_enabled(false)
            end;
        end;
    end;
    v_u_17.slot_place = function(_, p45) --[[ Name: slot_place ]] --[[ Line: 160 ]]
        --[[ Upvalues: (copy 1): p_u_14, (copy 2): v_u_36 ]]
        if p_u_14._players._slots:contains(p45) == false then
            return 0;
        end;
        local v46 = p_u_14._players._slots:get(p45)
        for v47 = 1, v_u_36:count() do
            if v_u_36:get(v47)._id == v46._id then
                return v47;
            end;
        end;
        return 0;
    end;
    f_cons()
    return v_u_17;
end;
return v7;
