-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:50 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUIChild)
require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Menu.MenuSystem)
require(game.ReplicatedStorage.Local.GameJoinProtocol)
local v_u_3 = require(game.ReplicatedStorage.Lobby.UI.MatchMakingV3Player)
require(game.ReplicatedStorage.AudioData.SongDatabase)
return {
    ["new"] = function(_, p4, _, _, p_u_5, p_u_6) --[[ Name: new ]] --[[ Line: 17 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_3, (copy 3): v_u_2 ]]
        local v7 = {}
        local v_u_8 = v_u_1:new()
        local l__game_join_protocol_0 = p4._game_join_protocol
        local v_u_9 = nil
        local v_u_10 = nil
        v7.cons = function(_) --[[ Name: cons ]] --[[ Line: 26 ]]
            --[[ Upvalues: (ref 1): v_u_9, (copy 2): p_u_5, (ref 3): v_u_10, (ref 4): v_u_1, (copy 5): v_u_8, (ref 6): v_u_3, (ref 7): v_u_2, (copy 8): p_u_6 ]]
            v_u_9 = p_u_5.MainSurface.SurfaceGui.Frame.MatchMakingSection.PlayersWaitingDisplay
            v_u_10 = p_u_5.MainSurface.SurfaceGui.Frame.MatchMakingSection.MatchIDDisplay
            local l_PlayerSlotProto_0 = p_u_5.PlayerSlotProto
            l_PlayerSlotProto_0.Parent = nil
            local l_PlayerSlotStatusIconProto_0 = p_u_5.PlayerSlotStatusIconProto
            l_PlayerSlotStatusIconProto_0.Parent = nil
            local v11 = v_u_1:new():push_back_table_list({
                p_u_5.Anchors.Slot1,
                p_u_5.Anchors.Slot2,
                p_u_5.Anchors.Slot3,
                p_u_5.Anchors.Slot4
            })
            for v12 = 1, v11:count() do
                local v13 = v11:get(v12)
                local v14 = l_PlayerSlotProto_0:Clone()
                v14.Parent = p_u_5
                local v15 = l_PlayerSlotStatusIconProto_0:Clone()
                v15.Parent = p_u_5
                v14.Position = v13.PlayerSlotProto.Position
                v15.Position = v13.PlayerSlotStatusIconProto.Position
                v_u_8:push_back(v_u_3:new(v14, v_u_2:new(p_u_6, p_u_5.MainSurface, v14), v15, v_u_2:new(p_u_6, p_u_5.MainSurface, v15)))
            end;
        end;
        local v_u_16 = -1
        v7.behaviour_update = function(_, p17, p18) --[[ Name: behaviour_update ]] --[[ Line: 64 ]]
            --[[ Upvalues: (copy 1): v_u_8, (ref 2): v_u_16, (copy 3): l__game_join_protocol_0, (ref 4): v_u_9, (ref 5): v_u_10 ]]
            for v19 = 1, v_u_8:count() do
                v_u_8:get(v19):behaviour_update(p17, p18)
            end;
            if v_u_16 ~= l__game_join_protocol_0:last_updated_time() then
                v_u_16 = l__game_join_protocol_0:last_updated_time()
                local v20 = l__game_join_protocol_0:get_slots()
                local v21 = l__game_join_protocol_0:mmv3_get_matchmaking_gameinstance_player_info()
                for v22 = 1, 4 do
                    local v23 = v20:get(v22)
                    local v24 = v_u_8:get(v22)
                    v24:set_player_data(v23)
                    v24:set_matchmaking_gameinstance_player_info(v23, v21[v22])
                end;
            end;
            if l__game_join_protocol_0:has_been_updated() then
                v_u_9.Text = string.format("%s (of %s)", tostring(l__game_join_protocol_0:mmv3_get_matchmaking_players_count()), (tostring(l__game_join_protocol_0:mmv3_get_matchmaking_queued_players_count())))
                v_u_10.Text = tostring(l__game_join_protocol_0:mmv3_get_gameid())
            else
                v_u_9.Text = "Loading..."
                v_u_10.Text = "Loading..."
            end;
        end;
        v7.layout = function(_) --[[ Name: layout ]] --[[ Line: 94 ]]
            --[[ Upvalues: (copy 1): v_u_8 ]]
            for v25 = 1, v_u_8:count() do
                v_u_8:get(v25):layout()
            end;
        end;
        v7:cons()
        return v7;
    end
};
