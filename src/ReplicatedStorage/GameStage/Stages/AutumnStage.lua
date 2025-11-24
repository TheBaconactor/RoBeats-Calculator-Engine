-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:08 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.GameStage.StageInfoBase)
local v_u_2 = require(game.ReplicatedStorage.Shared.Override)
require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_3 = require(game.ReplicatedStorage.Shared.GameSlot)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPVector)
require(game.ReplicatedStorage.Shared.PlayerSettings)
require(game.ReplicatedStorage.Shared.BrightnessSettings)
local v_u_5 = require(game.ReplicatedStorage.Shared.ModelLoadDB)
local v_u_6 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_7 = nil
local v_u_8 = nil
local v_u_9 = nil
require(game.ReplicatedStorage.Shared.Dependency):require_client(function() --[[ Line: 19 ]]
    --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_8, (ref 3): v_u_9 ]]
    v_u_7 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
    v_u_8 = require(game.ReplicatedStorage.GameStage.Util.GameStageDefaultCharacterShineBehaviour)
    v_u_9 = require(game.ReplicatedStorage.Effects.CharacterShineEffect)
end)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 27 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_5, (copy 4): v_u_6, (ref 5): v_u_7, (copy 6): v_u_4, (ref 7): v_u_8, (copy 8): v_u_3 ]]
        local v10 = v_u_1:new()
        v_u_2:get_base_fn(v10, "get_name")
        v10.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 31 ]]
            return "Autumn Abode";
        end;
        v_u_2:get_base_fn(v10, "get_icon")
        v10.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 33 ]]
            return "rbxassetid://15309921679";
        end;
        local v_u_11 = nil
        v10.load_stage = function(_, p_u_12) --[[ Name: load_stage ]] --[[ Line: 36 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_6, (ref 3): v_u_11 ]]
            v_u_5:singleton():load_model_category(v_u_6.GameStage.AutumnStage, v_u_6.Category.GameStage, function(p13) --[[ Line: 37 ]]
                --[[ Upvalues: (ref 1): v_u_11, (copy 2): p_u_12 ]]
                v_u_11 = p13
                p_u_12()
            end)
        end;
        local v_u_14 = nil
        local v_u_15 = nil
        local v_u_16 = nil
        v_u_2:get_base_fn(v10, "setup_stage")
        v10.setup_stage = function(p17, p18) --[[ Name: setup_stage ]] --[[ Line: 49 ]]
            --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_7, (ref 3): v_u_4, (ref 4): v_u_14, (ref 5): v_u_15, (ref 6): v_u_16, (ref 7): v_u_8 ]]
            v_u_11.Parent = v_u_7:get_local_elements_folder()
            local v19 = v_u_7:get_game_sky()
            v19.SkyboxBk = "rbxassetid://5674406298"
            v19.SkyboxDn = "rbxassetid://5674405985"
            v19.SkyboxFt = "rbxassetid://5674406449"
            v19.SkyboxLf = "rbxassetid://5674406184"
            v19.SkyboxRt = "rbxassetid://5674406378"
            v19.SkyboxUp = "rbxassetid://5674406072"
            local v20 = v_u_7:get_game_lighting()
            v20.Ambient = Color3.new(0.517647, 0.427451, 0.0980392)
            v20.Brightness = 1
            v20.ColorShift_Bottom = Color3.new(0.470588, 0.129412, 0.764706)
            v20.ColorShift_Top = Color3.new(0.14902, 0, 0.647059)
            v20.OutdoorAmbient = Color3.new(0.498039, 0.498039, 0.498039)
            v20.ClockTime = 12
            v20.GeographicLatitude = 45
            local v21 = v_u_7:get_game_atmosphere()
            v21.Density = 0.3
            v21.Offset = 0.25
            v21.Glare = 0
            v21.Haze = 0
            v21.Color = v_u_4:new(199, 199, 199):to_color3()
            v21.Decay = v_u_4:new(106, 112, 125):to_color3()
            v_u_7:set_game_atmosphere_enabled(true)
            v_u_14 = v_u_11
            p17:on_switch_focus_slot(p18)
            v_u_15 = v_u_11.CharacterShineProto
            v_u_15.Parent = nil
            v_u_16 = v_u_8:new(v_u_15, Vector3.new(0, -3.5, 0))
        end;
        v_u_2:get_base_fn(v10, "on_switch_focus_slot")
        v10.on_switch_focus_slot = function(_, p22) --[[ Name: on_switch_focus_slot ]] --[[ Line: 91 ]]
            --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_3 ]]
            v_u_14:SetPrimaryPartCFrame(CFrame.new(v_u_3:get_world_center_position(), v_u_3:slot_to_world_position(p22:get_local_game_slot())))
        end;
        v_u_2:get_base_fn(v10, "teardown_stage")
        v10.teardown_stage = function(_, p23) --[[ Name: teardown_stage ]] --[[ Line: 99 ]]
            --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_15, (ref 3): v_u_16, (ref 4): v_u_11 ]]
            v_u_14 = nil
            v_u_15:Destroy()
            v_u_16:teardown(p23)
            v_u_11:Destroy()
        end;
        v_u_2:get_base_fn(v10, "create_shine_for_slot_at_cframe")
        v10.create_shine_for_slot_at_cframe = function(_, p24, p25, p26) --[[ Name: create_shine_for_slot_at_cframe ]] --[[ Line: 109 ]]
            --[[ Upvalues: (ref 1): v_u_16 ]]
            v_u_16:create_shine_for_slot_at_cframe(p24, p25, p26)
        end;
        v_u_2:get_base_fn(v10, "game_update")
        v10.game_update = function(_, p27, p28) --[[ Name: game_update ]] --[[ Line: 114 ]]
            --[[ Upvalues: (ref 1): v_u_16 ]]
            v_u_16:update(p27, p28)
        end;
        v_u_2:get_base_fn(v10, "should_do_game_start_zoom_in_effect")
        v10.should_do_game_start_zoom_in_effect = function(_) --[[ Name: should_do_game_start_zoom_in_effect ]] --[[ Line: 119 ]]
            return true, 45.625, 24.5, 0.75;
        end;
        return v10;
    end
};
