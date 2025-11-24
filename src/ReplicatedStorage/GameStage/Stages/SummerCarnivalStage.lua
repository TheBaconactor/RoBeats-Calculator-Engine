-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:07 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.GameStage.StageInfoBase)
local v_u_2 = require(game.ReplicatedStorage.Shared.Override)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_4 = require(game.ReplicatedStorage.Shared.GameSlot)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPVector)
require(game.ReplicatedStorage.Shared.PlayerSettings)
require(game.ReplicatedStorage.Shared.BrightnessSettings)
local v_u_6 = require(game.ReplicatedStorage.Shared.ModelLoadDB)
local v_u_7 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_8 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_9 = nil
local v_u_10 = nil
local v_u_11 = nil
require(game.ReplicatedStorage.Shared.Dependency):require_client(function() --[[ Line: 18 ]]
    --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_10, (ref 3): v_u_11 ]]
    v_u_9 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
    v_u_10 = require(game.ReplicatedStorage.GameStage.Util.GameStageDefaultCharacterShineBehaviour)
    v_u_11 = require(game.ReplicatedStorage.Effects.CharacterShineEffect)
end)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 26 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_6, (copy 4): v_u_7, (ref 5): v_u_9, (copy 6): v_u_5, (ref 7): v_u_10, (copy 8): v_u_4, (copy 9): v_u_3, (copy 10): v_u_8 ]]
        local v12 = v_u_1:new()
        v_u_2:get_base_fn(v12, "get_name")
        v12.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 30 ]]
            return "Summertime Carnival";
        end;
        v_u_2:get_base_fn(v12, "get_icon")
        v12.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 32 ]]
            return "rbxassetid://14413301732";
        end;
        local v_u_13 = nil
        v12.load_stage = function(_, p_u_14) --[[ Name: load_stage ]] --[[ Line: 35 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_7, (ref 3): v_u_13 ]]
            v_u_6:singleton():load_model_category(v_u_7.GameStage.SummerCarnivalStage, v_u_7.Category.GameStage, function(p15) --[[ Line: 36 ]]
                --[[ Upvalues: (ref 1): v_u_13, (copy 2): p_u_14 ]]
                v_u_13 = p15
                p_u_14()
            end)
        end;
        local v_u_16 = nil
        local v_u_17 = nil
        local v_u_18 = nil
        local v_u_19 = nil
        v_u_2:get_base_fn(v12, "setup_stage")
        v12.setup_stage = function(p20, p21) --[[ Name: setup_stage ]] --[[ Line: 48 ]]
            --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_9, (ref 3): v_u_5, (ref 4): v_u_16, (ref 5): v_u_19, (ref 6): v_u_17, (ref 7): v_u_18, (ref 8): v_u_10 ]]
            v_u_13.Parent = v_u_9:get_local_elements_folder()
            local v22 = v_u_9:get_game_sky()
            v22.SkyboxBk = "rbxassetid://14213723003"
            v22.SkyboxDn = "rbxassetid://14213793809"
            v22.SkyboxFt = "rbxassetid://14213798092"
            v22.SkyboxLf = "rbxassetid://14213786569"
            v22.SkyboxRt = "rbxassetid://14213819768"
            v22.SkyboxUp = "rbxassetid://14213800754"
            local v23 = v_u_9:get_game_lighting()
            v23.Brightness = 0.65
            v23.Ambient = v_u_5:new(0, 0, 0):to_color3()
            v23.ColorShift_Bottom = v_u_5:new(120, 33, 195):to_color3()
            v23.ColorShift_Top = v_u_5:new(38, 0, 165):to_color3()
            local v24 = v_u_9:get_game_atmosphere()
            v24.Density = 0.35
            v24.Offset = 1
            v24.Glare = 0
            v24.Haze = 0
            v24.Color = v_u_5:new(0, 27, 199):to_color3()
            v24.Decay = v_u_5:new(22, 125, 17):to_color3()
            v_u_9:set_game_atmosphere_enabled(true)
            v_u_16 = v_u_13.FaceToPlayer
            v_u_19 = v_u_16.TrackPlatform.Union
            p20:on_switch_focus_slot(p21)
            v_u_17 = v_u_13.CharacterShineProto
            v_u_17.Parent = nil
            v_u_18 = v_u_10:new(v_u_17, Vector3.new(0, -3.9, 0))
        end;
        v_u_2:get_base_fn(v12, "on_switch_focus_slot")
        v12.on_switch_focus_slot = function(_, p25) --[[ Name: on_switch_focus_slot ]] --[[ Line: 90 ]]
            --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_4 ]]
            v_u_16:SetPrimaryPartCFrame(CFrame.new(v_u_4:get_world_center_position(), v_u_4:slot_to_world_position(p25:get_local_game_slot())))
        end;
        v_u_2:get_base_fn(v12, "teardown_stage")
        v12.teardown_stage = function(_, p26) --[[ Name: teardown_stage ]] --[[ Line: 98 ]]
            --[[ Upvalues: (ref 1): v_u_18, (ref 2): v_u_17, (ref 3): v_u_16, (ref 4): v_u_19, (ref 5): v_u_13 ]]
            v_u_18:teardown(p26)
            v_u_17:Destroy()
            v_u_16 = nil
            v_u_19 = nil
            v_u_13:Destroy()
        end;
        v_u_2:get_base_fn(v12, "create_shine_for_slot_at_cframe")
        v12.create_shine_for_slot_at_cframe = function(_, p27, p28, p29) --[[ Name: create_shine_for_slot_at_cframe ]] --[[ Line: 107 ]]
            --[[ Upvalues: (ref 1): v_u_18 ]]
            v_u_18:create_shine_for_slot_at_cframe(p27, p28, p29)
        end;
        v_u_2:get_base_fn(v12, "game_update")
        v12.game_update = function(_, p30, p31) --[[ Name: game_update ]] --[[ Line: 112 ]]
            --[[ Upvalues: (ref 1): v_u_18 ]]
            v_u_18:update(p30, p31)
        end;
        v_u_2:get_base_fn(v12, "should_do_game_start_zoom_in_effect")
        v12.should_do_game_start_zoom_in_effect = function(_) --[[ Name: should_do_game_start_zoom_in_effect ]] --[[ Line: 117 ]]
            return true, 45.625, 16.099999999999998, 0.75;
        end;
        v12.game_camera_transition = function(_, p_u_32) --[[ Name: game_camera_transition ]] --[[ Line: 121 ]]
            --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_3, (ref 3): v_u_8 ]]
            if v_u_19 then
                v_u_3:ptry(function() --[[ Line: 123 ]]
                    --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_3, (ref 3): v_u_8, (copy 4): p_u_32 ]]
                    v_u_19.Transparency = v_u_3:tra(v_u_8:YForPointOf2PtLineP1P2X(0, 0, 1, 0.6, p_u_32))
                end)
            end;
        end;
        return v12;
    end
};
