-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:50 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Shared.SPUIChild)
require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Menu.MenuSystem)
require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_4 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_5 = require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_6 = require(game.ReplicatedStorage.PlayerInfo.PlatformPlayerRewardInfo)
return {
    ["new"] = function(_, p_u_7, _, p_u_8) --[[ Name: new ]] --[[ Line: 16 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_3, (copy 3): v_u_4, (copy 4): v_u_2, (copy 5): v_u_5, (copy 6): v_u_6 ]]
        local v9 = {}
        local v_u_10 = false
        local v_u_11 = 0
        v9.cons = function(_) --[[ Name: cons ]] --[[ Line: 22 ]]
            --[[ Upvalues: (ref 1): v_u_11, (copy 2): p_u_8, (ref 3): v_u_10 ]]
            v_u_11 = 0
            p_u_8:get_child_part().SurfaceGui.Enabled = false
            p_u_8:set_scale(0)
            v_u_10 = false
        end;
        v9.behaviour_update = function(_, p12) --[[ Name: behaviour_update ]] --[[ Line: 29 ]]
            --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_11, (ref 3): v_u_1, (ref 4): v_u_3, (copy 5): p_u_8 ]]
            if v_u_10 ~= false then
                local v13 = v_u_11
                v_u_11 = v_u_1:clamp(v_u_11 + v_u_3:SecondsToTick(0.75) * p12, 0, 1)
                if v_u_11 ~= v13 then
                    p_u_8:set_scale(v_u_3:BezierValForT(Vector2.new(0, 0), Vector2.new(0.5, 1.5), Vector2.new(0.5, 1), Vector2.new(1, 1), v_u_11).Y)
                end;
            end;
        end;
        v9.load_reward_info = function(_, p14) --[[ Name: load_reward_info ]] --[[ Line: 43 ]]
            --[[ Upvalues: (copy 1): p_u_8, (ref 2): v_u_4, (ref 3): v_u_2, (copy 4): p_u_7, (ref 5): v_u_1, (ref 6): v_u_5, (ref 7): v_u_6, (ref 8): v_u_10 ]]
            local v15 = p_u_8:get_child_part()
            local l_Frame_0 = v15.SurfaceGui.Frame
            v15.SurfaceGui.Enabled = true
            local l_MatchCoinReward_0 = p14.MatchCoinReward
            local l_VIPCoinBonusReward_0 = p14.VIPCoinBonusReward
            v_u_4:is_int(l_VIPCoinBonusReward_0)
            local l_PlayerCount_0 = p14.PlayerCount
            local l_Place_0 = p14.Place
            local l_QuitEarly_0 = p14.QuitEarly
            local l_SpectateCheerCoins_0 = p14.SpectateCheerCoins
            local l_SpectateCheerCount_0 = p14.SpectateCheerCount
            local v16 = v_u_2:new():push_back_table_list({ l_Frame_0.Bonus1, l_Frame_0.Bonus2, l_Frame_0.Bonus3 })
            local v17 = v16:count()
            if p_u_7:is_spectate() ~= true and l_MatchCoinReward_0 > 0 then
                local v18 = v16:pop_front()
                v18.Title.Text = "[Reward]"
                if l_PlayerCount_0 == 0 then
                    v18.BonusDisplay.Text = "Solo Match"
                else
                    v18.BonusDisplay.Text = string.format("%s place in match of %d (%s).", v_u_1:num_placify(l_Place_0), l_PlayerCount_0, v_u_1:enum_val_to_name(v_u_5:get_selected_mode(), v_u_5))
                end;
                v18.ValueDisplay.Text = tostring(l_MatchCoinReward_0)
                v_u_6:local_flag_as_having_completed_match(p_u_7)
            end;
            if l_SpectateCheerCount_0 > 0 and v16:count() > 0 then
                local v19 = v16:pop_front()
                v19.Title.Text = "[Reward]"
                if p_u_7:is_spectate() then
                    v19.BonusDisplay.Text = string.format("Cheered %d time(s).", l_SpectateCheerCount_0)
                else
                    v19.BonusDisplay.Text = string.format("Recieved %d cheer(s).", l_SpectateCheerCount_0)
                end;
                v19.ValueDisplay.Text = tostring(l_SpectateCheerCoins_0)
            end;
            if l_VIPCoinBonusReward_0 > 0 and v16:count() > 0 then
                local v20 = v16:pop_front()
                v20.Title.Text = "[Bonus]"
                v20.BonusDisplay.Text = string.format("VIP Bonus")
                v20.ValueDisplay.Text = tostring(l_VIPCoinBonusReward_0)
            end;
            for v21 = 1, v16:count() do
                v16:get(v21).Visible = false
            end;
            local l_EmptyDisplay_0 = l_Frame_0.EmptyDisplay
            if v16:count() == v17 then
                l_EmptyDisplay_0.Visible = true
                if p_u_7:is_spectate() then
                    l_EmptyDisplay_0.Text = "Cheer on players when spectating and earn rewards!"
                elseif l_QuitEarly_0 == true then
                    l_EmptyDisplay_0.Text = "Match ended early."
                else
                    l_EmptyDisplay_0.Text = "Did not earn any rewards for this match."
                end;
            else
                l_EmptyDisplay_0.Visible = false
            end;
            v_u_10 = true
        end;
        v9.layout = function(_) --[[ Name: layout ]] --[[ Line: 135 ]]
            --[[ Upvalues: (copy 1): p_u_8 ]]
            p_u_8:layout()
        end;
        v9:cons()
        return v9;
    end
};
