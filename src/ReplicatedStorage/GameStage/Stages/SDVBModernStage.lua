-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:06 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.GameStage.StageInfoBase)
local v_u_2 = require(game.ReplicatedStorage.Shared.Override)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_4 = require(game.ReplicatedStorage.Shared.GameSlot)
local v_u_5 = require(game.ReplicatedStorage.Shared.NoteSkinColor)
local v_u_6 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_7 = require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_8 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_9 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_10 = require(game.ReplicatedStorage.Shared.ModelLoadDB)
local v_u_11 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_12 = nil
local v_u_13 = nil
local v_u_14 = nil
require(game.ReplicatedStorage.Shared.Dependency):require_client(function() --[[ Line: 20 ]]
    --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_13, (ref 3): v_u_14 ]]
    v_u_12 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
    v_u_13 = require(game.ReplicatedStorage.GameStage.Util.GameStageDefaultCharacterShineBehaviour)
    v_u_14 = require(game.ReplicatedStorage.Effects.CharacterShineEffect)
end)
local v15 = {}
local function f_create_trigger_button_asset(p_u_16, p_u_17, p18, p19) --[[ Name: create_trigger_button_asset ]] --[[ Line: 28 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_8, (copy 3): v_u_3, (copy 4): v_u_5, (copy 5): v_u_2, (copy 6): v_u_6, (copy 7): v_u_7 ]]
    local v_u_20 = p19:Clone()
    local v21 = v_u_1.TriggerButtonAsset:new(p_u_16, p_u_17, p18, v_u_20)
    local v_u_22 = 0.1
    local v_u_23 = v_u_8:new()
    local v_u_24 = nil
    local function _() --[[ Name: cons ]] --[[ Line: 40 ]]
        --[[ Upvalues: (ref 1): v_u_24, (copy 2): v_u_20, (copy 3): v_u_23, (ref 4): v_u_3 ]]
        v_u_24 = v_u_20.ButtonHighlight
        v_u_23:push_back_table_list({ v_u_20.ButtonHighlight, v_u_20.ButtonDetails })
        v_u_24.Transparency = v_u_3:tra(0.1)
    end;
    local v_u_25 = v_u_5:get_default_base_color():to_color3()
    local v_u_26 = v_u_5:get_default_fever_color():to_color3()
    v_u_2:get_base_fn(v21, "set_game_noteskin_colors")
    v21.set_game_noteskin_colors = function(_, p27, p28) --[[ Name: set_game_noteskin_colors ]] --[[ Line: 52 ]]
        --[[ Upvalues: (ref 1): v_u_25, (ref 2): v_u_26 ]]
        v_u_25 = p27
        v_u_26 = p28
    end;
    v_u_2:get_base_fn(v21, "on_press")
    v21.on_press = function(_) --[[ Name: on_press ]] --[[ Line: 58 ]]
        --[[ Upvalues: (ref 1): v_u_22 ]]
        v_u_22 = 0.75
    end;
    v_u_2:get_base_fn(v21, "on_release")
    v21.on_release = function(_) --[[ Name: on_release ]] --[[ Line: 63 ]]
        --[[ Upvalues: (ref 1): v_u_22 ]]
        v_u_22 = 0.1
    end;
    v_u_2:get_base_fn(v21, "update")
    v21.update = function(_, p29) --[[ Name: update ]] --[[ Line: 68 ]]
        --[[ Upvalues: (copy 1): p_u_17, (copy 2): p_u_16, (ref 3): v_u_24, (ref 4): v_u_6, (ref 5): v_u_3, (ref 6): v_u_22, (ref 7): v_u_25, (ref 8): v_u_7, (ref 9): v_u_26, (copy 10): v_u_23 ]]
        if p_u_17 == p_u_16:get_local_game_slot() then
            v_u_24.Transparency = v_u_6:Expt(v_u_24.Transparency, v_u_3:tra(v_u_22), v_u_6:NormalizedDefaultExptValueInSeconds(0.45), p29)
            local v30 = v_u_25
            if v_u_7:get_server_game_instance_player_powerbar_active(p_u_16._players._slots:get(p_u_17)) then
                v30 = v_u_26
            end;
            for _, v31 in v_u_23:key_itr() do
                v31.Color = v30
            end;
        end;
    end;
    v_u_24 = v_u_20.ButtonHighlight
    v_u_23:push_back_table_list({ v_u_20.ButtonHighlight, v_u_20.ButtonDetails })
    v_u_24.Transparency = v_u_3:tra(0.1)
    return v21;
end;
v15.new = function(_) --[[ Name: new ]] --[[ Line: 91 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_10, (copy 4): v_u_11, (ref 5): v_u_12, (ref 6): v_u_13, (copy 7): v_u_9, (copy 8): v_u_6, (copy 9): v_u_3, (copy 10): v_u_4, (copy 11): v_u_7, (copy 12): f_create_trigger_button_asset ]]
    local v32 = v_u_1:new()
    v_u_2:get_base_fn(v32, "get_name")
    v32.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 95 ]]
        return "Radiant Colors (SDVB)";
    end;
    v_u_2:get_base_fn(v32, "get_icon")
    v32.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 97 ]]
        return "rbxassetid://9583129331";
    end;
    local v_u_33 = nil
    v32.load_stage = function(_, p_u_34) --[[ Name: load_stage ]] --[[ Line: 100 ]]
        --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_11, (ref 3): v_u_33 ]]
        v_u_10:singleton():load_model_category(v_u_11.GameStage.SDVBModernStage, v_u_11.Category.GameStage, function(p35) --[[ Line: 101 ]]
            --[[ Upvalues: (ref 1): v_u_33, (copy 2): p_u_34 ]]
            v_u_33 = p35
            p_u_34()
        end)
    end;
    local v_u_36 = nil
    local v_u_37 = nil
    local v_u_38 = nil
    local v_u_39 = nil
    local v_u_40 = nil
    local v_u_41 = nil
    local v_u_42 = nil
    local v_u_43 = 0
    local v_u_44 = nil
    local v_u_45 = nil
    local v_u_46 = nil
    local v_u_47 = nil
    v_u_2:get_base_fn(v32, "setup_stage")
    v32.setup_stage = function(p48, p49) --[[ Name: setup_stage ]] --[[ Line: 119 ]]
        --[[ Upvalues: (ref 1): v_u_36, (ref 2): v_u_33, (ref 3): v_u_37, (ref 4): v_u_38, (ref 5): v_u_12, (ref 6): v_u_39, (ref 7): v_u_40, (ref 8): v_u_41, (ref 9): v_u_42, (ref 10): v_u_47, (ref 11): v_u_13, (ref 12): v_u_44, (ref 13): v_u_45, (ref 14): v_u_46, (ref 15): v_u_9, (ref 16): v_u_6, (ref 17): v_u_3 ]]
        v_u_36 = v_u_33.Stage
        v_u_37 = v_u_33.CharacterShineProto
        v_u_38 = v_u_33.TriggerButtonProto
        local v50 = v_u_12:get_game_sky()
        v50.SkyboxBk = "http://www.roblox.com/asset/?id=12733682"
        v50.SkyboxDn = "http://www.roblox.com/asset/?id=12733682"
        v50.SkyboxFt = "http://www.roblox.com/asset/?id=12733682"
        v50.SkyboxLf = "http://www.roblox.com/asset/?id=12733682"
        v50.SkyboxRt = "http://www.roblox.com/asset/?id=12733682"
        v50.SkyboxUp = "http://www.roblox.com/asset/?id=12733682"
        p48:on_switch_focus_slot(p49)
        v_u_36.Parent = v_u_12:get_local_elements_folder()
        v_u_38.Parent = nil
        v_u_39 = v_u_36.CenterEmitter.BillboardGui.Frame.Glow1
        v_u_40 = v_u_36.CenterEmitter.BillboardGui.Frame.Glow2
        v_u_41 = v_u_36.CenterEmitter.BillboardGui.Frame.Glow3
        v_u_42 = v_u_36.CenterEmitter.BillboardGui.Frame.Glow4
        v_u_47 = v_u_13:new(v_u_37, Vector3.new(0, -3.5, 0))
        if p49:show_fullscreen_mobile_ui() then
            v_u_36.ButtonPanelPC.Parent = nil
            v_u_36.TrackHighlightPC.Parent = nil
            v_u_44 = v_u_36.ButtonPanelMobile.KnobLeft.GlowHead
            v_u_45 = v_u_36.ButtonPanelMobile.KnobRight.GlowHead
        else
            v_u_36.ButtonPanelMobile.Parent = nil
            v_u_36.TrackHighlightMobile.Parent = nil
            v_u_44 = v_u_36.ButtonPanelPC.KnobLeft.GlowHead
            v_u_45 = v_u_36.ButtonPanelPC.KnobRight.GlowHead
        end;
        v_u_46 = v_u_36.ButtonFC.Cover
        local v51 = v_u_6:YForPointOf2PtLineP1P2X(5, -0.4, 30, -2, v_u_3:clamp(v_u_9:singleton():get_difficulty_for_key(p49:es_gamelocal_get_audiomanager():get_song_key()), 5, 30))
        v_u_36.TextureMotion.LeftBeamNormal.TextureSpeed = v51
        v_u_36.TextureMotion.LeftBeamClear.TextureSpeed = v51 * 0.5
        v_u_36.TextureMotion.RightBeamNormal.TextureSpeed = v51
        v_u_36.TextureMotion.RightBeamClear.TextureSpeed = v51 * 0.5
    end;
    v_u_2:get_base_fn(v32, "on_switch_focus_slot")
    v32.on_switch_focus_slot = function(_, p52) --[[ Name: on_switch_focus_slot ]] --[[ Line: 171 ]]
        --[[ Upvalues: (ref 1): v_u_36, (ref 2): v_u_4 ]]
        v_u_36:SetPrimaryPartCFrame(CFrame.new(v_u_4:get_world_center_position(), v_u_4:slot_to_world_position(p52:get_local_game_slot())))
    end;
    v_u_2:get_base_fn(v32, "create_shine_for_slot_at_cframe")
    v32.create_shine_for_slot_at_cframe = function(_, p53, p54, p55) --[[ Name: create_shine_for_slot_at_cframe ]] --[[ Line: 179 ]]
        --[[ Upvalues: (ref 1): v_u_47 ]]
        v_u_47:create_shine_for_slot_at_cframe(p53, p54, p55)
    end;
    v_u_2:get_base_fn(v32, "teardown_stage")
    v32.teardown_stage = function(_, p56) --[[ Name: teardown_stage ]] --[[ Line: 184 ]]
        --[[ Upvalues: (ref 1): v_u_47, (ref 2): v_u_33, (ref 3): v_u_36, (ref 4): v_u_37, (ref 5): v_u_38 ]]
        v_u_47:teardown(p56)
        v_u_33:Destroy()
        v_u_36:Destroy()
        v_u_37:Destroy()
        v_u_38:Destroy()
    end;
    v_u_2:get_base_fn(v32, "game_update")
    v32.game_update = function(_, p57, p58) --[[ Name: game_update ]] --[[ Line: 193 ]]
        --[[ Upvalues: (ref 1): v_u_47, (ref 2): v_u_7, (ref 3): v_u_44, (ref 4): v_u_46, (ref 5): v_u_39, (ref 6): v_u_40, (ref 7): v_u_41, (ref 8): v_u_42, (ref 9): v_u_45, (ref 10): v_u_43, (ref 11): v_u_6, (ref 12): v_u_3 ]]
        v_u_47:update(p57, p58)
        local v59 = p58:get_game_note_skin_info()
        local v60 = v59:get_slot_basecolor_list(p58:get_local_game_slot())
        local v61 = v59:get_slot_fevercolor_list(p58:get_local_game_slot())
        local v62, v63, v64, v65
        if v_u_7:get_server_game_instance_player_powerbar_active(p58._players._slots:get(p58:get_local_game_slot())) then
            v62 = v61:get(1):to_color3()
            v63 = v61:get(2):to_color3()
            v64 = v61:get(3):to_color3()
            v65 = v61:get(4):to_color3()
        else
            v62 = v60:get(1):to_color3()
            v63 = v60:get(2):to_color3()
            v64 = v60:get(3):to_color3()
            v65 = v60:get(4):to_color3()
        end;
        v_u_44.Color = v62
        v_u_46.Color = v63
        v_u_39.ImageColor3 = v64
        v_u_40.ImageColor3 = v64:Lerp(Color3.new(), 0.35)
        v_u_41.ImageColor3 = v64:Lerp(Color3.new(), 0.5)
        v_u_42.ImageColor3 = v64:Lerp(Color3.new(), 0.85)
        v_u_45.Color = v65
        v_u_43 = v_u_6:IncrementWrap(v_u_43, v_u_6:SecondsToTick(1.75) * p57, 1)
        local v66 = v_u_6:YForPointOf2PtLineP1P2X(-1, 0.75, 1, 1, (math.sin(v_u_43 * 2 * 3.141592653589793)))
        v_u_39.ImageTransparency = v_u_3:tra(v66)
        v_u_40.ImageTransparency = v_u_3:tra(v66 * 0.5)
        v_u_41.ImageTransparency = v_u_3:tra(v66 * 0.25)
        v_u_42.ImageTransparency = v_u_3:tra(v66 * 0.25)
    end;
    v_u_2:get_base_fn(v32, "create_trigger_button_asset")
    v32.create_trigger_button_asset = function(_, p67, p68, p69) --[[ Name: create_trigger_button_asset ]] --[[ Line: 236 ]]
        --[[ Upvalues: (ref 1): f_create_trigger_button_asset, (ref 2): v_u_38 ]]
        return f_create_trigger_button_asset(p67, p68, p69, v_u_38);
    end;
    return v32;
end;
return v15;
