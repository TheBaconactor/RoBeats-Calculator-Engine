-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:27 PM
-- Cached decompilation

require(game.ReplicatedStorage.Local.DebugOut)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_4 = require(game.ReplicatedStorage.Shared.PlayerStatus)
return {
    ["new"] = function(_, p_u_5) --[[ Name: new ]] --[[ Line: 12 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_4, (copy 3): v_u_1, (copy 4): v_u_3 ]]
        local v6 = {}
        local v_u_7 = v_u_2:new()
        local v_u_8 = nil
        local v_u_9 = nil
        local function f_F(p10) --[[ Name: F ]] --[[ Line: 18 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_7 ]]
            local v11 = v_u_4:tablelist_to_list(p10)
            for v12 = 1, v11:count() do
                local v13 = v11:get(v12)
                v13:set_last_modified(tick())
                v_u_7:add(v13:get_player_id(), v13)
            end;
        end;
        v6.cons = function(_) --[[ Name: cons ]] --[[ Line: 27 ]]
            --[[ Upvalues: (copy 1): p_u_5, (ref 2): v_u_1, (copy 3): f_F, (copy 4): v_u_7, (ref 5): v_u_8, (ref 6): v_u_9, (ref 7): v_u_4 ]]
            p_u_5._evt:wait_on_event_once(v_u_1.EVT_PlayerStatus_ServerRespondInitial, function(p14) --[[ Line: 28 ]]
                --[[ Upvalues: (ref 1): f_F ]]
                f_F(p14)
            end)
            p_u_5._evt:fire_event_to_server(v_u_1.EVT_PlayerStatus_ClientRequestInitial)
            p_u_5._evt:wait_on_event(v_u_1.EVT_PlayerStatus_ServerUpdate, function(p15) --[[ Line: 33 ]]
                --[[ Upvalues: (ref 1): f_F ]]
                f_F(p15)
            end)
            game.Players.PlayerRemoving:connect(function(p16) --[[ Line: 37 ]]
                --[[ Upvalues: (ref 1): v_u_7 ]]
                v_u_7:remove(p16.UserId)
            end)
            local v17, v18 = v_u_4:backup_cleanup()
            v_u_8 = v17
            v_u_9 = v18
        end;
        v6.get_id_to_playerstatus_dict = function(_) --[[ Name: get_id_to_playerstatus_dict ]] --[[ Line: 44 ]]
            --[[ Upvalues: (copy 1): v_u_7 ]]
            return v_u_7;
        end;
        v6.contains_status_for_id = function(_, p19) --[[ Name: contains_status_for_id ]] --[[ Line: 46 ]]
            --[[ Upvalues: (copy 1): v_u_7 ]]
            return v_u_7:contains(p19);
        end;
        v6.get_status_for_id = function(_, p20) --[[ Name: get_status_for_id ]] --[[ Line: 47 ]]
            --[[ Upvalues: (copy 1): v_u_7, (ref 2): v_u_4 ]]
            if v_u_7:contains(p20) == true then
                return v_u_7:get(p20);
            else
                return v_u_4:new(p20);
            end;
        end;
        v6.update = function(_, p21) --[[ Name: update ]] --[[ Line: 52 ]]
            --[[ Upvalues: (copy 1): v_u_7, (ref 2): v_u_4, (ref 3): v_u_3, (ref 4): v_u_8, (ref 5): v_u_9 ]]
            for _, v22 in v_u_7:key_itr() do
                if v22:get_mode() == v_u_4.Mode.MatchPlaying then
                    v22:set_playback_time_sec((v_u_3:IncrementClamp(v22:get_playback_time_sec(), v_u_3:TimescaleToDeltaTime(p21), 0, v22:get_sound_length_sec())))
                end;
            end;
            v_u_8:update(p21)
            if v_u_8:do_flash() then
                v_u_9(v_u_7)
            end;
        end;
        v6:cons()
        return v6;
    end
};
