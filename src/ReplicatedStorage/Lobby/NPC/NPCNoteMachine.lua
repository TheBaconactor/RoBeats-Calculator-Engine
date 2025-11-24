-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:37 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Local.AnimationManager)
local v_u_2 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_3 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_4 = require(game.ReplicatedStorage.Lobby.NPC.NPCAsyncLoad)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_6 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_7 = require(game.ReplicatedStorage.Lobby.Menus.CraftingGatchaUI)
return {
    ["new"] = function(_, p8, p9) --[[ Name: new ]] --[[ Line: 13 ]]
        --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_6, (copy 3): v_u_4, (copy 4): v_u_3, (copy 5): v_u_1, (copy 6): v_u_7, (copy 7): v_u_2 ]]
        local v_u_10 = nil
        local v_u_11 = nil
        local v_u_12 = nil
        local v_u_13 = 0
        local v_u_14 = 0
        local function f_define_local_fns(p15) --[[ Name: define_local_fns ]] --[[ Line: 22 ]]
            --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_13, (ref 3): v_u_12, (ref 4): v_u_5, (ref 5): v_u_11, (ref 6): v_u_10, (ref 7): v_u_6 ]]
            p15.show_fade_back = function(_, p16) --[[ Name: show_fade_back ]] --[[ Line: 23 ]]
                --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_13, (ref 3): v_u_12, (ref 4): v_u_5 ]]
                if p16 == true then
                    v_u_14 = 0.85
                else
                    v_u_13 = 0
                    v_u_14 = 0
                    v_u_12.Transparency = v_u_5:tra(0)
                end;
            end;
            p15.play_idle_anim = function(p17) --[[ Name: play_idle_anim ]] --[[ Line: 33 ]]
                --[[ Upvalues: (ref 1): v_u_11 ]]
                p17:play_anim(v_u_11)
            end;
            p15.stop_anim = function(p18) --[[ Name: stop_anim ]] --[[ Line: 37 ]]
                p18:play_anim(nil)
            end;
            p15.show_face_neutral = function(_) --[[ Name: show_face_neutral ]] --[[ Line: 41 ]]
                --[[ Upvalues: (ref 1): v_u_10 ]]
                v_u_10.Face.SurfaceGui.Frame.MachineSelected.Visible = false
                v_u_10.Face.SurfaceGui.Frame.FaceNeutral.Visible = true
            end;
            p15.show_face_machine_selected = function(_) --[[ Name: show_face_machine_selected ]] --[[ Line: 45 ]]
                --[[ Upvalues: (ref 1): v_u_10 ]]
                v_u_10.Face.SurfaceGui.Frame.MachineSelected.Visible = true
                v_u_10.Face.SurfaceGui.Frame.FaceNeutral.Visible = false
            end;
            p15.update = function(p19, p20) --[[ Name: update ]] --[[ Line: 50 ]]
                --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_14, (ref 3): v_u_6, (ref 4): v_u_12, (ref 5): v_u_5 ]]
                p19:update_base(p20)
                if v_u_13 ~= v_u_14 then
                    v_u_13 = v_u_6:Expt(v_u_13, v_u_14, v_u_6:NormalizedDefaultExptValueInSeconds(0.5), p20)
                    v_u_12.Transparency = v_u_5:tra(v_u_13)
                end;
            end;
            p15.get_nametag_position_offset = function(_) --[[ Name: get_nametag_position_offset ]] --[[ Line: 63 ]]
                return Vector3.new(0, 5.5, 0);
            end;
        end;
        return v_u_4:new(p8, p9, v_u_3.NPC.NPC_NoteMachine, "NoteBot", "Craft Material Machine", game.ReplicatedStorage.LobbyElementProtos.CharacterOverlay.DialoguePopupNoteMachine, true, function(p21, p22, _) --[[ Line: 74 ]]
            --[[ Upvalues: (copy 1): f_define_local_fns, (ref 2): v_u_10, (ref 3): v_u_12, (ref 4): v_u_11, (ref 5): v_u_1 ]]
            f_define_local_fns(p21)
            v_u_10 = p22
            v_u_12 = v_u_10.FadeBack
            v_u_11 = p21:load_anim(v_u_10.Humanoid, v_u_1.ANIM_STARMACHINE_BOUNCE)
            p21:play_idle_anim()
            p21:show_face_neutral()
        end, function(p23, p24, p25) --[[ Line: 84 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_2 ]]
            p25:push_menu(v_u_7:new(p23, p24, p25))
            p23._sfx_manager:play_sfx(v_u_2.SFX_MENU_OPEN)
        end);
    end
};
