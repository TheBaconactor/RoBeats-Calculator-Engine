-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:36 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Local.AnimationManager)
local v_u_2 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_3 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_4 = require(game.ReplicatedStorage.Lobby.NPC.NPCAsyncLoad)
return {
    ["new"] = function(_, p5, p6) --[[ Name: new ]] --[[ Line: 9 ]]
        --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_3, (copy 3): v_u_1, (copy 4): v_u_2 ]]
        return v_u_4:new(p5, p6, v_u_3.NPC.NPC_spotco, "Helpful Alien", "Practice", game.ReplicatedStorage.LobbyElementProtos.CharacterOverlay.DialoguePopupPractice, true, function(p7, _, p8) --[[ Line: 18 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            p7:play_anim((p7:load_anim(p8, v_u_1.ANIM_OLDSCHOOLSHUFFLE)))
        end, function(p9, _, _) --[[ Line: 22 ]]
            --[[ Upvalues: (ref 1): v_u_2 ]]
            p9._sfx_manager:play_sfx(v_u_2.SFX_MENU_OPEN)
            p9._spectate_manager:show_song_select_preview_menu()
        end);
    end
};
