-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:29 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Shared.ChainCombo)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_3 = require(game.ReplicatedStorage.GameUI.ComboNotifDisplay)
require(game.ReplicatedStorage.Local.DebugOut)
local v_u_4 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.Shared.EventString)
local v_u_5 = require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_6 = require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_7 = require(game.ReplicatedStorage.LocalShared.FrameIndex)
return {
    ["new"] = function(_, p_u_8) --[[ Name: new ]] --[[ Line: 18 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_5, (copy 3): v_u_4, (copy 4): v_u_3, (copy 5): v_u_2, (copy 6): v_u_6, (copy 7): v_u_7 ]]
        local v_u_9 = v_u_1:SPUIObjectBase()
        v_u_9._obj = nil
        local v_u_10 = nil
        local function f_cons() --[[ Name: cons ]] --[[ Line: 25 ]]
            --[[ Upvalues: (copy 1): v_u_9, (copy 2): p_u_8, (ref 3): v_u_5, (ref 4): v_u_4, (ref 5): v_u_10, (ref 6): v_u_3, (ref 7): v_u_2 ]]
            v_u_9._obj = game.ReplicatedStorage.WorldUIProto.ComboNotif:Clone()
            if p_u_8._player_settings_manager:get_key(v_u_5.Key.ShowComboDisplay) then
                v_u_9._obj.Parent = v_u_4:get_world_ui_folder()
            end;
            v_u_9._native_size = v_u_9._obj.PrimaryPart.Size
            v_u_9._size = v_u_9._native_size
            v_u_10 = v_u_3:new(v_u_9._obj.ScaleSurface.SurfaceGui.Frame.ComboNotif1, v_u_9._obj.ScaleSurface.SurfaceGui.Frame.ComboNotif2, v_u_9._obj.ScaleSurface.SurfaceGui.Frame.ComboNotif3, v_u_9._obj.ScaleSurface.SurfaceGui.Frame.ComboNotif4, v_u_9._obj.ScaleSurface.SurfaceGui.Frame.ComboDisplay, v_u_9._obj.ScaleSurface.SurfaceGui.Frame.MultiplierDisplay, v_u_2:new(v_u_9, v_u_9._obj.PrimaryPart, v_u_9._obj.ScaleSurface), p_u_8, p_u_8:get_local_game_slot())
            v_u_9:layout()
        end;
        v_u_9.teardown = function(p11) --[[ Name: teardown ]] --[[ Line: 52 ]]
            --[[ Upvalues: (ref 1): v_u_10 ]]
            v_u_10:teardown()
            p11._obj:Destroy()
            p11._obj = nil
        end;
        v_u_9.update_visual = function(_, p12, _) --[[ Name: update_visual ]] --[[ Line: 58 ]]
            --[[ Upvalues: (copy 1): p_u_8, (ref 2): v_u_6, (ref 3): v_u_10 ]]
            local v13 = p_u_8:es_gamelocal_get_audiomanager():is_playing() == true and 1 or 0
            local v14, v15 = p_u_8:es_gamelocal_get_scoremanager():get_score_objs()
            local v16, v17
            if v_u_6:get_selected_mode() == v_u_6.Compete then
                v16 = v14:get_chain()
                v17 = v14:get_chain_multiplier()
            else
                v16 = v15:get_chain()
                v17 = v15:get_chain_multiplier()
            end;
            v_u_10:update_with_chain_value(p12, v16, v17, v13)
        end;
        local v_u_18 = v_u_1:cframe_params_default()
        v_u_18.PositionNXY:set(1, 1)
        v_u_18.LocalRotationOffset:set(0, -5, 0)
        local l__spui_0 = p_u_8._spui
        v_u_9.layout = function(p19) --[[ Name: layout ]] --[[ Line: 87 ]]
            --[[ Upvalues: (copy 1): p_u_8, (copy 2): l__spui_0, (copy 3): v_u_18 ]]
            if p_u_8:show_fullscreen_mobile_ui() then
                p19:opt_rescale_to_max_nxy(l__spui_0, 0.2, 0.2)
                v_u_18.OffsetXYZ:from_vector3(p19:anchored_offset(1, 1) + Vector3.new(-l__spui_0:get_size_from_nxy(0, 0).X, l__spui_0:get_size_from_nxy(0, 0).Y))
            else
                p19:opt_rescale_to_max_nxy(l__spui_0, 0.2, 0.2)
                v_u_18.OffsetXYZ:from_vector3(p19:anchored_offset(1, 1) + Vector3.new(-l__spui_0:get_size_from_nxy(0, 0).X, l__spui_0:get_size_from_nxy(0, 0).Y))
            end;
            local v20, v21 = p19:opt_update_cframe_params(l__spui_0, v_u_18)
            if v20 == true then
                p19._obj:SetPrimaryPartCFrame(v21)
            end;
        end;
        v_u_9.get_native_size = function(p22) --[[ Name: get_native_size ]] --[[ Line: 109 ]]
            return p22._native_size;
        end;
        v_u_9.get_size = function(p23) --[[ Name: get_size ]] --[[ Line: 112 ]]
            return p23._size;
        end;
        v_u_9.set_size = function(p24, p25) --[[ Name: set_size ]] --[[ Line: 115 ]]
            p24._size = p25
            p24._obj.PrimaryPart.Size = Vector3.new(p25.X, p25.Y, 0)
        end;
        local l_GameComboNotif_0 = v_u_7.Test.GameComboNotif
        v_u_7:register_ui_needs_refresh_should_run_test_type(l_GameComboNotif_0)
        v_u_9.update = function(p26, _, _) --[[ Name: update ]] --[[ Line: 122 ]]
            --[[ Upvalues: (ref 1): v_u_7, (copy 2): l_GameComboNotif_0, (copy 3): p_u_8 ]]
            local v27 = v_u_7:singleton()
            if v27:should_run(l_GameComboNotif_0) ~= false then
                local v28 = v27:get_test_state(l_GameComboNotif_0):get_dt_scale()
                p26:layout()
                p26:update_visual(v28, p_u_8)
            end;
        end;
        f_cons()
        return v_u_9;
    end
};
