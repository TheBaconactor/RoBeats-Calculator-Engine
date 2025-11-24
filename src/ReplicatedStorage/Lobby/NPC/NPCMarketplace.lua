-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:37 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Local.AnimationManager)
local v_u_2 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_3 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_4 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_5 = require(game.ReplicatedStorage.Lobby.NPC.NPCAsyncLoad)
local v_u_6 = require(game.ReplicatedStorage.Lobby.Menus.MarketplaceUI)
return {
    ["new"] = function(_, p7, p8) --[[ Name: new ]] --[[ Line: 11 ]]
        --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_4, (copy 3): v_u_1, (copy 4): v_u_3, (copy 5): v_u_6, (copy 6): v_u_2 ]]
        return v_u_5:new(p7, p8, v_u_4.NPC.NPC_Marketplace, "Marsha", "Marketplace", game.ReplicatedStorage.LobbyElementProtos.CharacterOverlay.DialoguePopupMarketplace, true, function(p9, _, p10) --[[ Line: 20 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            p9:play_anim((p9:load_anim(p10, v_u_1.ANIM_MARKETPLACE_IDLE)))
        end, function(p11, p12, p13) --[[ Line: 24 ]]
            --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_6, (ref 3): v_u_2 ]]
            if v_u_3.TradeEnabled == true then
                p13:push_menu(v_u_6:new(p11, p12, p13))
            end;
            p11._sfx_manager:play_sfx(v_u_2.SFX_MENU_OPEN)
        end);
    end
};
