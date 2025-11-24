-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:27 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_2 = require(game.ReplicatedStorage.GameUI.PlaceSlotManager)
local v_u_3 = require(game.ReplicatedStorage.GameUI.PowerBarManager)
local v_u_4 = require(game.ReplicatedStorage.GameUI.ComboNotifManager)
require(game.ReplicatedStorage.Local.DebugOut)
local v_u_5 = require(game.ReplicatedStorage.GameUI.RankBar)
local v_u_6 = require(game.ReplicatedStorage.GameUI.PreStartCountdown)
require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_7 = require(game.ReplicatedStorage.GameUI.TouchDisplay)
local v_u_8 = require(game.ReplicatedStorage.GameUI.TutorialIngameOverlay)
local v_u_9 = require(game.ReplicatedStorage.GameUI.ControlPopupManager)
local v_u_10 = require(game.ReplicatedStorage.GameUI.MissionDisplay)
local v_u_11 = require(game.ReplicatedStorage.Local.DecalUIManager)
local v_u_12 = require(game.ReplicatedStorage.GameUI.SongTimeDisplay)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_13 = require(game.ReplicatedStorage.LocalShared.FrameIndex)
local v_u_14 = require(game.ReplicatedStorage.GameUI.QuitDisplayV2)
return {
    ["new"] = function(_, p_u_15) --[[ Name: new ]] --[[ Line: 25 ]]
        --[[ Upvalues: (copy 1): v_u_11, (copy 2): v_u_2, (copy 3): v_u_3, (copy 4): v_u_4, (copy 5): v_u_12, (copy 6): v_u_5, (copy 7): v_u_6, (copy 8): v_u_7, (copy 9): v_u_14, (copy 10): v_u_8, (copy 11): v_u_9, (copy 12): v_u_10, (copy 13): v_u_13, (copy 14): v_u_1 ]]
        local v16 = {
            ["_place_slots"] = nil,
            ["_power_bar"] = nil,
            ["_combo_notif"] = nil,
            ["_rank_bar"] = nil,
            ["_pre_start_countdown"] = nil
        }
        local v_u_17 = false
        local v_u_18 = nil
        local v_u_19 = nil
        local v_u_20 = nil
        local v_u_21 = nil
        local v_u_22 = nil
        local v_u_23 = nil
        local v_u_24 = nil
        v16.get_decal_ui_manager = function(_) --[[ Name: get_decal_ui_manager ]] --[[ Line: 43 ]]
            --[[ Upvalues: (ref 1): v_u_24 ]]
            return v_u_24;
        end;
        v16.init = function(_, p25) --[[ Name: init ]] --[[ Line: 45 ]]
            --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_11 ]]
            v_u_24 = v_u_11:new(p25)
        end;
        v16.initialize_ui = function(p26, p_u_27) --[[ Name: initialize_ui ]] --[[ Line: 50 ]]
            --[[ Upvalues: (copy 1): p_u_15, (ref 2): v_u_2, (ref 3): v_u_3, (ref 4): v_u_4, (ref 5): v_u_18, (ref 6): v_u_12, (ref 7): v_u_5, (ref 8): v_u_6, (ref 9): v_u_19, (ref 10): v_u_7, (ref 11): v_u_20, (ref 12): v_u_14, (ref 13): v_u_21, (ref 14): v_u_8, (ref 15): v_u_22, (ref 16): v_u_9, (ref 17): v_u_23, (ref 18): v_u_10, (ref 19): v_u_17 ]]
            p_u_15:layout()
            p26._place_slots = v_u_2:new(p_u_27)
            p26._power_bar = v_u_3:new(p_u_27)
            p26._combo_notif = v_u_4:new(p_u_27)
            v_u_18 = v_u_12:new(p_u_27)
            p26._rank_bar = v_u_5:new(p_u_27)
            p26._pre_start_countdown = v_u_6:new(p_u_27)
            v_u_19 = v_u_7:new(p_u_27)
            v_u_20 = v_u_14:new(p_u_27, function() --[[ Line: 61 ]]
                --[[ Upvalues: (copy 1): p_u_27 ]]
                p_u_27:early_quit()
            end)
            v_u_21 = v_u_8:new(p_u_27)
            v_u_22 = v_u_9:new(p_u_27)
            v_u_23 = v_u_10:new(p_u_27)
            v_u_17 = true
            p_u_15:layout()
        end;
        v16.teardown = function(p28) --[[ Name: teardown ]] --[[ Line: 73 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_18, (ref 3): v_u_19, (ref 4): v_u_20, (ref 5): v_u_21, (ref 6): v_u_22, (ref 7): v_u_23, (ref 8): v_u_24 ]]
            if v_u_17 == true then
                p28._place_slots:teardown()
                p28._power_bar:teardown()
                p28._combo_notif:teardown()
                v_u_18:teardown()
                p28._rank_bar:teardown()
                p28._pre_start_countdown:teardown()
                v_u_19:teardown()
                v_u_20:teardown()
                v_u_21:teardown()
                v_u_22:teardown()
                v_u_23:teardown()
                v_u_24:teardown()
                v_u_17 = false
            end;
        end;
        local l_GameQuitDisplay_0 = v_u_13.Test.GameQuitDisplay
        v_u_13:register_ui_needs_refresh_should_run_test_type(l_GameQuitDisplay_0)
        v16.update = function(p29, p30, p31) --[[ Name: update ]] --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_1, (ref 3): v_u_24, (ref 4): v_u_18, (ref 5): v_u_13, (copy 6): l_GameQuitDisplay_0, (ref 7): v_u_20, (ref 8): v_u_22, (ref 9): v_u_19, (ref 10): v_u_21, (ref 11): v_u_23 ]]
            if v_u_17 == true then
                v_u_1:profilebegin("UIManager:update")
                v_u_24:update(p30)
                v_u_1:profilebegin("self._place_slots:update()")
                p29._place_slots:update(p30, p31)
                v_u_1:profileend()
                v_u_1:profilebegin("self._power_bar:update()")
                p29._power_bar:update(p30, p31)
                v_u_1:profileend()
                v_u_1:profilebegin("self._combo_notif:update()")
                p29._combo_notif:update(p30, p31)
                v_u_1:profileend()
                v_u_1:profilebegin("self._song_marker:update()")
                v_u_18:update(p30, p31)
                v_u_1:profileend()
                v_u_1:profilebegin("self._rank_bar:update()")
                p29._rank_bar:update(p30, p31)
                v_u_1:profileend()
                v_u_1:profilebegin("self._pre_start_countdown:update()")
                p29._pre_start_countdown:update(p30, p31)
                v_u_1:profileend()
                v_u_1:profilebegin("quit_display + control_popup_manager")
                local v32 = v_u_13:singleton()
                if v32:should_run(l_GameQuitDisplay_0) then
                    local v33 = v32:get_test_state(l_GameQuitDisplay_0)
                    local v34 = v33:get_dt_scale()
                    p31._input:set_frame_index_state(v33)
                    v_u_20:update(v34, p31)
                    v_u_22:update(v34, p31)
                    p31._input:set_frame_index_state(nil)
                end;
                v_u_1:profileend()
                v_u_1:profilebegin("touch_display+tutorial_ingame_overlay")
                v_u_19:update(p30, p31)
                v_u_21:update(p30, p31)
                v_u_1:profileend()
                v_u_1:profilebegin("mission_display")
                v_u_23:update(p30, p31)
                v_u_1:profileend()
                v_u_1:profileend()
            end;
        end;
        v16.add_control_popup = function(_, p35, p36) --[[ Name: add_control_popup ]] --[[ Line: 155 ]]
            --[[ Upvalues: (ref 1): v_u_22 ]]
            v_u_22:add_control_popup(p35, p36)
        end;
        return v16;
    end
};
