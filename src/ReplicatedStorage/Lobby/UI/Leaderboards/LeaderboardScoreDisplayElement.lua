-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:54 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUIChild)
require(game.ReplicatedStorage.Menu.SPUIButton)
require(game.ReplicatedStorage.Menu.MenuSystem)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Local.SFXManager)
return {
    ["new"] = function(_, p3, p4, p_u_5) --[[ Name: new ]] --[[ Line: 12 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1 ]]
        local v6 = v_u_2:new(p3, p4, p_u_5)
        local v_u_7 = nil
        local v_u_8 = nil
        local v_u_9 = nil
        local v_u_10 = nil
        local v_u_11 = nil
        local v_u_12 = nil
        local v_u_13 = nil
        v6.cons = function(p14) --[[ Name: cons ]] --[[ Line: 23 ]]
            --[[ Upvalues: (copy 1): p_u_5, (ref 2): v_u_7, (ref 3): v_u_8, (ref 4): v_u_9, (ref 5): v_u_10, (ref 6): v_u_11, (ref 7): v_u_12, (ref 8): v_u_13 ]]
            p14:set_sgui(p_u_5.SurfaceGui)
            v_u_7 = p_u_5.SurfaceGui.PlayerProto
            v_u_8 = v_u_7.NameDisplay
            v_u_9 = v_u_7.Bubble.PlaceDisplay
            v_u_10 = v_u_7.GearMultiplierDisplay
            v_u_11 = v_u_7.ScoreDisplay
            v_u_12 = v_u_7.Bubble
            v_u_13 = v_u_7.PlayerIconDisplay
        end;
        v6.set_info = function(p15, p16) --[[ Name: set_info ]] --[[ Line: 34 ]]
            --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_9, (ref 3): v_u_1, (ref 4): v_u_10, (ref 5): v_u_11, (ref 6): v_u_13, (ref 7): v_u_12 ]]
            if p16.Valid == true then
                p15:set_ui_visible(true)
            else
                p15:set_ui_visible(false)
            end;
            v_u_8.Text = p16.PlayerName
            v_u_9.Text = v_u_1:num_placify(p16.Place)
            v_u_10.Text = string.format("%.2f", p16.GearMult)
            v_u_11.Text = v_u_1:comma_value(p16.Score)
            v_u_1:get_user_thumbnail(p16.RbxID, function(p17) --[[ Line: 44 ]]
                --[[ Upvalues: (ref 1): v_u_13 ]]
                v_u_13.Image = p17
            end, false)
            if p16.Place == 1 then
                v_u_12.Image = v_u_1:get_leaderboard_bubble_gold_assetid()
                return;
            elseif p16.Place <= 10 then
                v_u_12.Image = v_u_1:get_leaderboard_bubble_silver_assetid()
                return;
            elseif p16.Place <= 50 then
                v_u_12.Image = v_u_1:get_leaderboard_bubble_bronze_assetid()
            else
                v_u_12.Image = v_u_1:get_leaderboard_bubble_none_assetid()
            end;
        end;
        v6.set_ui_visible = function(_, p18) --[[ Name: set_ui_visible ]] --[[ Line: 56 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            v_u_7.Visible = p18
        end;
        v6:cons()
        return v6;
    end
};
