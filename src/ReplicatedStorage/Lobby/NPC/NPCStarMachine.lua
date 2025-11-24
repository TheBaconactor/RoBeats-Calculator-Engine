-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:35 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Local.AnimationManager)
local v_u_2 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_3 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_4 = require(game.ReplicatedStorage.Lobby.NPC.NPCAsyncLoad)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_6 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_7 = require(game.ReplicatedStorage.Lobby.Menus.SongGatchaUI)
return {
    ["new"] = function(_, p8, p9) --[[ Name: new ]] --[[ Line: 13 ]]
        --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_6, (copy 3): v_u_4, (copy 4): v_u_3, (copy 5): v_u_1, (copy 6): v_u_7, (copy 7): v_u_2 ]]
        local v_u_10 = nil
        local v_u_11 = nil
        local v_u_12 = nil
        local v_u_13 = nil
        local v_u_14 = 0
        local v_u_15 = 0
        local function f_define_local_fns(p16) --[[ Name: define_local_fns ]] --[[ Line: 22 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_14, (ref 3): v_u_11, (ref 4): v_u_5, (ref 5): v_u_10, (ref 6): v_u_12, (ref 7): v_u_13, (ref 8): v_u_6 ]]
            p16.show_fade_back = function(_, p17) --[[ Name: show_fade_back ]] --[[ Line: 23 ]]
                --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_14, (ref 3): v_u_11, (ref 4): v_u_5 ]]
                if p17 == true then
                    v_u_15 = 0.85
                else
                    v_u_14 = 0
                    v_u_15 = 0
                    v_u_11.Transparency = v_u_5:tra(0)
                end;
            end;
            p16.play_idle_anim = function(p18) --[[ Name: play_idle_anim ]] --[[ Line: 33 ]]
                --[[ Upvalues: (ref 1): v_u_10 ]]
                p18:play_anim(v_u_10)
            end;
            p16.stop_anim = function(p19) --[[ Name: stop_anim ]] --[[ Line: 37 ]]
                p19:play_anim(nil)
            end;
            p16.show_face_neutral = function(_) --[[ Name: show_face_neutral ]] --[[ Line: 41 ]]
                --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_13 ]]
                v_u_12.Visible = false
                v_u_13.Visible = true
            end;
            p16.show_face_machine_selected = function(_) --[[ Name: show_face_machine_selected ]] --[[ Line: 45 ]]
                --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_13 ]]
                v_u_12.Visible = true
                v_u_13.Visible = false
            end;
            p16.update = function(p20, p21) --[[ Name: update ]] --[[ Line: 50 ]]
                --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_15, (ref 3): v_u_6, (ref 4): v_u_11, (ref 5): v_u_5 ]]
                p20:update_base(p21)
                if v_u_14 ~= v_u_15 then
                    v_u_14 = v_u_6:Expt(v_u_14, v_u_15, v_u_6:NormalizedDefaultExptValueInSeconds(0.5), p21)
                    v_u_11.Transparency = v_u_5:tra(v_u_14)
                end;
            end;
            p16.get_nametag_position_offset = function(_) --[[ Name: get_nametag_position_offset ]] --[[ Line: 63 ]]
                return Vector3.new(0, 5.5, 0);
            end;
        end;
        return v_u_4:new(p8, p9, v_u_3.NPC.NPC_StarMachine, "SongBot5000", "Song Machine", game.ReplicatedStorage.LobbyElementProtos.CharacterOverlay.DialoguePopupStarMachine, true, function(p22, p23, p24) --[[ Line: 74 ]]
            --[[ Upvalues: (copy 1): f_define_local_fns, (ref 2): v_u_10, (ref 3): v_u_1, (ref 4): v_u_11, (ref 5): v_u_12, (ref 6): v_u_13 ]]
            f_define_local_fns(p22)
            v_u_10 = p22:load_anim(p24, v_u_1.ANIM_STARMACHINE_BOUNCE)
            v_u_11 = p23.FadeBack
            v_u_12 = p23.Screen.SurfaceGui.Frame.MachineSelected
            v_u_13 = p23.Screen.SurfaceGui.Frame.FaceNeutral
            p22:play_idle_anim()
            p22:show_face_neutral()
        end, function(p25, p26, p27) --[[ Line: 85 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_2 ]]
            p27:push_menu(v_u_7:new(p25, p26, p27))
            p25._sfx_manager:play_sfx(v_u_2.SFX_MENU_OPEN)
        end);
    end
};
