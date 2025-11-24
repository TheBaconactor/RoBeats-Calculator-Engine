-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:01 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.GuildUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.GuildData)
local v_u_3 = require(game.ReplicatedStorage.SPChat.Shared.SPChatMessage)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_5 = require(game.ReplicatedStorage.Shared.Mutex)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_6 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_7 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_8 = require(game.ReplicatedStorage.Shared.SPDict)
local v9 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_10 = nil
local v_u_11 = nil
local v_u_12 = nil
v9:require_client(function() --[[ Line: 18 ]]
    --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_11, (ref 3): v_u_12 ]]
    v_u_10 = require(game.ReplicatedStorage.Lobby.Menus.GuildInfoUI)
    v_u_11 = require(game.ReplicatedStorage.Lobby.Menus.GuildViewUI)
    v_u_12 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
end)
return {
    ["new"] = function(_, p_u_13) --[[ Name: new ]] --[[ Line: 26 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_8, (copy 3): v_u_2, (copy 4): v_u_3, (copy 5): v_u_4, (ref 6): v_u_11, (ref 7): v_u_10, (copy 8): v_u_6, (copy 9): v_u_5, (copy 10): v_u_7 ]]
        local v_u_14 = {}
        local v_u_15 = v_u_1:not_in_guild_id()
        local v_u_16 = v_u_8:new()
        local v_u_17 = 0
        local function f_cons() --[[ Name: cons ]] --[[ Line: 33 ]]
            --[[ Upvalues: (copy 1): p_u_13, (ref 2): v_u_2, (copy 3): v_u_16, (ref 4): v_u_17, (copy 5): v_u_14, (ref 6): v_u_3, (ref 7): v_u_4 ]]
            p_u_13._evt:wait_on_event(v_u_2.EVT_Guild_GetPlayerStatus_ServerResponse, function(p18) --[[ Line: 34 ]]
                --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_17 ]]
                v_u_16:add_table(p18)
                v_u_17 = tick()
            end)
            p_u_13._evt:wait_on_event(v_u_2.EVT_GuildRecruitment_AcceptInvite_ServerResponse, function(_, p19, p20) --[[ Line: 39 ]]
                --[[ Upvalues: (ref 1): v_u_14, (ref 2): p_u_13, (ref 3): v_u_3, (ref 4): v_u_4 ]]
                v_u_14:handle_player_info_server_response(true, p20)
                p_u_13._chat:get_system_channel():add_message_to_channel(v_u_3:new(p19):set_icon(v_u_4:important_assetid()))
            end)
        end;
        v_u_14.get_status_dict = function(_) --[[ Name: get_status_dict ]] --[[ Line: 45 ]]
            --[[ Upvalues: (copy 1): v_u_16, (ref 2): v_u_17 ]]
            return v_u_16, v_u_17;
        end;
        v_u_14.request_status_for_rbxid_list = function(_, p21) --[[ Name: request_status_for_rbxid_list ]] --[[ Line: 46 ]]
            --[[ Upvalues: (copy 1): p_u_13, (ref 2): v_u_2 ]]
            p_u_13._evt:fire_event_to_server(v_u_2.EVT_Guild_GetPlayerStatus_Client, p21:get_table())
        end;
        v_u_14.player_has_guild = function(_) --[[ Name: player_has_guild ]] --[[ Line: 50 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_1 ]]
            return v_u_15 ~= v_u_1:not_in_guild_id();
        end;
        v_u_14.get_player_guildid = function(_) --[[ Name: get_player_guildid ]] --[[ Line: 51 ]]
            --[[ Upvalues: (ref 1): v_u_15 ]]
            return v_u_15;
        end;
        v_u_14.show_guild_info_action = function(p22, p23) --[[ Name: show_guild_info_action ]] --[[ Line: 53 ]]
            --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_10 ]]
            if p22:player_has_guild() then
                p23._menus:push_menu(v_u_11:new(p23, p23._spui, p23._menus))
            else
                p23._menus:push_menu(v_u_10:new(p23, p23._spui, p23._menus))
            end;
        end;
        v_u_14.handle_player_info_server_response = function(_, p24, p25) --[[ Name: handle_player_info_server_response ]] --[[ Line: 61 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_15, (ref 3): v_u_1 ]]
            if p24 then
                v_u_6:is_int(p25)
                v_u_15 = p25
            else
                v_u_15 = v_u_1:not_in_guild_id()
            end;
        end;
        local v_u_26 = v_u_5:new()
        v_u_14.accept_invite_to_join_guild = function(p_u_27, p_u_28) --[[ Name: accept_invite_to_join_guild ]] --[[ Line: 73 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_26, (copy 3): p_u_13, (ref 4): v_u_2, (ref 5): v_u_3, (ref 6): v_u_4 ]]
            v_u_5:critical_section(function() --[[ Line: 74 ]]
                --[[ Upvalues: (ref 1): v_u_26 ]]
                return v_u_26:test(1);
            end, function() --[[ Line: 76 ]]
                --[[ Upvalues: (ref 1): v_u_26 ]]
                v_u_26:retain(1)
            end, function() --[[ Line: 78 ]]
                --[[ Upvalues: (ref 1): v_u_26 ]]
                v_u_26:release(1)
            end, function() --[[ Line: 80 ]]
                --[[ Upvalues: (ref 1): v_u_26, (ref 2): p_u_13, (ref 3): v_u_2, (copy 4): p_u_27, (copy 5): p_u_28, (ref 6): v_u_3, (ref 7): v_u_4 ]]
                v_u_26:retain(1)
                p_u_13._evt:wait_on_event_once(v_u_2.EVT_Guild_AcceptInvite_ServerResponse, function(_, p29) --[[ Line: 82 ]]
                    --[[ Upvalues: (ref 1): p_u_27, (ref 2): p_u_28, (ref 3): p_u_13, (ref 4): v_u_3, (ref 5): v_u_4, (ref 6): v_u_26 ]]
                    p_u_27:handle_player_info_server_response(true, p_u_28)
                    p_u_13._chat:get_system_channel():add_message_to_channel(v_u_3:new(p29):set_icon(v_u_4:important_assetid()))
                    v_u_26:release(1)
                end)
                p_u_13._evt:fire_event_to_server(v_u_2.EVT_Guild_AcceptInvite_Client, p_u_28)
            end)
        end;
        v_u_14.get_time_to_next_week_sec = function(_) --[[ Name: get_time_to_next_week_sec ]] --[[ Line: 91 ]]
            --[[ Upvalues: (copy 1): p_u_13 ]]
            return p_u_13._player_blob_manager:get_time_to_next_week_sec();
        end;
        v_u_14.get_week_id = function(_) --[[ Name: get_week_id ]] --[[ Line: 92 ]]
            --[[ Upvalues: (copy 1): p_u_13 ]]
            return p_u_13._player_blob_manager:get_week_id();
        end;
        v_u_14.move_camera_to_guild_position = function(_, p30) --[[ Name: move_camera_to_guild_position ]] --[[ Line: 94 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            p30:set_character_random_position_around_anchors_fn(function() --[[ Line: 95 ]]
                --[[ Upvalues: (ref 1): v_u_7 ]]
                return v_u_7:get_lobby_anchors().Guild.StandAnchor, v_u_7:get_lobby_anchors().Guild.LookAnchor;
            end)
            p30:transition_local_camera_to_anchors_fn(function() --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_7 ]]
                return v_u_7:get_lobby_anchors().Guild.CameraAnchor, v_u_7:get_lobby_anchors().Guild.LookAnchor;
            end)
        end;
        v_u_14.update = function(_, p31) --[[ Name: update ]] --[[ Line: 105 ]]
            --[[ Upvalues: (copy 1): v_u_26 ]]
            v_u_26:update(p31)
        end;
        f_cons()
        return v_u_14;
    end
};
