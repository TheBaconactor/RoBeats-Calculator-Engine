-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:36 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Local.AnimationManager)
local v_u_2 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_3 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_4 = require(game.ReplicatedStorage.Lobby.NPC.NPCAsyncLoad)
local v5 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_6 = nil
v5:require_client(function() --[[ Line: 9 ]]
    --[[ Upvalues: (ref 1): v_u_6 ]]
    v_u_6 = require(game.ReplicatedStorage.Lobby.Menus.RobuxShopUI)
end)
return {
    ["new"] = function(_, p7, p8) --[[ Name: new ]] --[[ Line: 15 ]]
        --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_3, (copy 3): v_u_1, (ref 4): v_u_6, (copy 5): v_u_2 ]]
        return v_u_4:new(p7, p8, v_u_3.NPC.NPC_Roxie, "Roxie", "Robux Shop", game.ReplicatedStorage.LobbyElementProtos.CharacterOverlay.DialoguePopupRobuxShop, true, function(p9, _, p10) --[[ Line: 24 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            p9:play_anim((p9:load_anim(p10, v_u_1.ANIM_MATTIE_TALK)))
        end, function(p11, p12, p13) --[[ Line: 28 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_2 ]]
            p13:push_menu(v_u_6:new(p11, p12, p13))
            p11._sfx_manager:play_sfx(v_u_2.SFX_MENU_OPEN)
        end);
    end
};
