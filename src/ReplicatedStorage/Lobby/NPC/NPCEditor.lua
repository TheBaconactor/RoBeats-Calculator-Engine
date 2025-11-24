-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:38 PM
-- Cached decompilation

require(game.ReplicatedStorage.Local.AnimationManager)
local v_u_1 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_2 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_3 = require(game.ReplicatedStorage.Lobby.NPC.NPCAsyncLoad)
local v_u_4 = require(game.ReplicatedStorage.EditorGame.UI.SavedMapInfoListUI)
return {
    ["new"] = function(_, p5, p6) --[[ Name: new ]] --[[ Line: 10 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2, (copy 3): v_u_4, (copy 4): v_u_1 ]]
        return v_u_3:new(p5, p6, v_u_2.NPC.NPC_Editor, "R-Cade Robot", "Custom Map Robo-Butler", game.ReplicatedStorage.LobbyElementProtos.CharacterOverlay.DialoguePopupEditor, true, function(p7, _, p8) --[[ Line: 19 ]]
            p7:play_anim(p7:load_anim(p8, "rbxassetid://87633584872749"))
        end, function(p9, _, _) --[[ Line: 22 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_1 ]]
            v_u_4:show_editor_menu(p9)
            p9._sfx_manager:play_sfx(v_u_1.SFX_MENU_OPEN)
        end);
    end
};
