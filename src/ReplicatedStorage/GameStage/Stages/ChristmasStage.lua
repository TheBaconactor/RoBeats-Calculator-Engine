-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:07 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.GameStage.StageInfoBase)
local v_u_2 = require(game.ReplicatedStorage.Shared.Override)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.Shared.SPVector)
local v_u_4 = require(game.ReplicatedStorage.Shared.GameSlot)
require(game.ReplicatedStorage.Shared.MatchMode)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_5 = require(game.ReplicatedStorage.Shared.ModelLoadDB)
local v_u_6 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_7 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_8 = nil
local v_u_9 = nil
local v_u_10 = nil
local v_u_11 = nil
require(game.ReplicatedStorage.Shared.Dependency):require_client(function() --[[ Line: 19 ]]
    --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_9, (ref 3): v_u_10, (ref 4): v_u_11 ]]
    v_u_8 = require(game.ReplicatedStorage.Shared.BrightnessSettings)
    v_u_9 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
    v_u_10 = require(game.ReplicatedStorage.GameStage.Util.GameStageDefaultCharacterShineBehaviour)
    v_u_11 = require(game.ReplicatedStorage.Effects.CharacterShineEffect)
end)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 28 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_5, (copy 4): v_u_6, (ref 5): v_u_9, (ref 6): v_u_10, (copy 7): v_u_7, (copy 8): v_u_3, (copy 9): v_u_4 ]]
        local v12 = v_u_1:new()
        v_u_2:get_base_fn(v12, "get_name")
        v12.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 32 ]]
            return "Holiday Hamlet";
        end;
        v_u_2:get_base_fn(v12, "get_icon")
        v12.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 34 ]]
            return "rbxassetid://11732457887";
        end;
        local v_u_13 = nil
        v12.load_stage = function(_, p_u_14) --[[ Name: load_stage ]] --[[ Line: 37 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_6, (ref 3): v_u_13 ]]
            v_u_5:singleton():load_model_category(v_u_6.GameStage.ChristmasStage, v_u_6.Category.GameStage, function(p15) --[[ Line: 38 ]]
                --[[ Upvalues: (ref 1): v_u_13, (copy 2): p_u_14 ]]
                v_u_13 = p15
                p_u_14()
            end)
        end;
        local v_u_16 = nil
        local v_u_17 = nil
        local v_u_18 = nil
        v_u_2:get_base_fn(v12, "setup_stage")
        v12.setup_stage = function(p19, p20) --[[ Name: setup_stage ]] --[[ Line: 48 ]]
            --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_13, (ref 3): v_u_9, (ref 4): v_u_17, (ref 5): v_u_10, (ref 6): v_u_18, (ref 7): v_u_7, (ref 8): v_u_3 ]]
            v_u_16 = v_u_13.CharacterShineProto
            v_u_16.Parent = nil
            v_u_13.Parent = v_u_9:get_local_elements_folder()
            v_u_17 = v_u_10:new(v_u_16, Vector3.new(0, -3.5, 0))
            v_u_18 = v_u_13.FaceToPlayer
            for _, v_u_21 in v_u_7:new({ v_u_18.NPC_Santa.Humanoid }):key_itr() do
                local l_Animation_0 = Instance.new("Animation")
                l_Animation_0.AnimationId = "rbxassetid://507770818"
                v_u_3:ptry(function() --[[ Line: 65 ]]
                    --[[ Upvalues: (copy 1): v_u_21, (copy 2): l_Animation_0 ]]
                    v_u_21:LoadAnimation(l_Animation_0):Play()
                end)
            end;
            p19:on_switch_focus_slot(p20)
            local v22 = v_u_9:get_game_sky()
            v22.SkyboxBk = "rbxassetid://11306279518"
            v22.SkyboxDn = "rbxassetid://11306281020"
            v22.SkyboxFt = "rbxassetid://11306281859"
            v22.SkyboxLf = "rbxassetid://11306282757"
            v22.SkyboxRt = "rbxassetid://11306283490"
            v22.SkyboxUp = "rbxassetid://11306284442"
            local v23 = v_u_9:get_game_lighting()
            v23.Ambient = Color3.new(0.278431, 0.372549, 0.458824)
            v23.Brightness = 0
            v23.ColorShift_Bottom = Color3.new(0.764706, 0.345098, 0.0470588)
            v23.ColorShift_Top = Color3.new(0.635294, 0.490196, 0.32549)
            v23.OutdoorAmbient = Color3.new(0.278431, 0.372549, 0.458824)
            v23.ClockTime = 15
            v23.GeographicLatitude = 0
        end;
        v_u_2:get_base_fn(v12, "on_switch_focus_slot")
        v12.on_switch_focus_slot = function(_, p24) --[[ Name: on_switch_focus_slot ]] --[[ Line: 91 ]]
            --[[ Upvalues: (ref 1): v_u_18, (ref 2): v_u_4 ]]
            v_u_18:SetPrimaryPartCFrame(CFrame.new(v_u_4:get_world_center_position(), v_u_4:slot_to_world_position(p24:get_local_game_slot())))
        end;
        v_u_2:get_base_fn(v12, "create_shine_for_slot_at_cframe")
        v12.create_shine_for_slot_at_cframe = function(_, p25, p26, p27) --[[ Name: create_shine_for_slot_at_cframe ]] --[[ Line: 99 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            v_u_17:create_shine_for_slot_at_cframe(p25, p26, p27)
        end;
        v_u_2:get_base_fn(v12, "process_character_location_for_slot")
        v12.process_character_location_for_slot = function(_, p28, p29, p30, p31) --[[ Name: process_character_location_for_slot ]] --[[ Line: 104 ]]
            return p28, p29, p30, p31;
        end;
        v_u_2:get_base_fn(v12, "game_update")
        v12.game_update = function(_, p32, p33) --[[ Name: game_update ]] --[[ Line: 109 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            v_u_17:update(p32, p33)
        end;
        v_u_2:get_base_fn(v12, "teardown_stage")
        v12.teardown_stage = function(_, p34) --[[ Name: teardown_stage ]] --[[ Line: 114 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_16, (ref 3): v_u_18, (ref 4): v_u_13 ]]
            v_u_17:teardown(p34)
            v_u_16:Destroy()
            v_u_18:Destroy()
            v_u_13:Destroy()
        end;
        v_u_2:get_base_fn(v12, "should_do_game_start_zoom_in_effect")
        v12.should_do_game_start_zoom_in_effect = function(_) --[[ Name: should_do_game_start_zoom_in_effect ]] --[[ Line: 122 ]]
            return true, 36.5, 16.8, 0.75;
        end;
        return v12;
    end
};
