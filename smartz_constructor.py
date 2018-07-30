from smartz.api.constructor_engine import ConstructorInstance
# see https://github.com/smartzplatform/SDK


class Constructor(ConstructorInstance):

    def get_version(self):
        return {
            "result": "success",
            "blockchain": "eos",
            "version": 2
        }

    def get_params(self):
        json_schema = {
            "type": "object",
            "required": [
                "ticker", "decimals"
            ],
            "additionalProperties": False,

            "properties": {
                "ticker": {
                    "title": "Token ticker",
                    "description": "Only uppercase symbols (with length 3-7)",
                    "type": "string",
                    "minLength": 3,
                    "maxLength": 7,
                    "pattern": "^[A-Z][A-Z0-5]+$"
                },

                "decimals": {
                    "title": "Decimals",
                    "description": "Token decimals (0..8)",
                    "type": "integer",
                    "min": 0,
                    "max": 8
                },
            }
        }

        ui_schema = {}

        return {
            "result": "success",
            "schema": json_schema,
            "ui_schema": ui_schema
        }

    def construct(self, fields):
        source = self.__class__._TEMPLATE \
            .replace('%decimals%', str(fields['decimals'])) \
            .replace('%ticker%', fields['ticker'])

        return {
            "result": "success",
            'source': source,
            'contract_name': "simpletoken"
        }

    def post_construct(self, fields, abi_array):

        function_specs = {
            'transfer': {
                'title': 'Transfer',
                'description': 'Transfer tokens',
                'inputs': [
                    {'title': 'From', 'description': "Account to transfer tokens from"},
                    {'title': 'To', 'description': "Account to transfer tokens"},
                    {'title': 'Quantity', 'description': "Tokens quantity in format '123.456 TICKER'"}
                ]
            },

            'issue': {
                'title': 'Issue',
                'description': 'Issue new tokens',
                'inputs': [
                    {'title': 'To', 'description': "Account to issue tokens for"},
                    {'title': 'Quantity', 'description': "Tokens quantity in format '123.456 TICKER'"}
                ]
            },

            'totalSupply': {
                'title': 'Total supply',
            },
            'account': {
                'title': 'Get balance',
                'inputs': [
                    {'title': 'Account name'},
                ]
            },
        }

        return {
            "result": "success",
            'function_specs': function_specs,
            'dashboard_functions': ['totalSupply']
        }


    # language=Solidity
    _TEMPLATE = """
#include <eosiolib/eosio.hpp>
#include <eosiolib/asset.hpp>

static constexpr uint64_t token_symbol = S(%decimals%, %ticker%); // precision, symbol

using eosio::asset;

class simpletoken : public eosio::contract {
   public:
      simpletoken( account_name self ):
        contract(self),
        _accounts( _self, _self),
        _state(_self, _self)
        {}

      // @abi action
      void transfer( account_name from, account_name to, asset quantity ) {
         require_auth( from );
         eosio_assert( quantity.symbol == token_symbol, "wrong symbol" );

         const auto& fromacnt = _accounts.get( from );
         eosio_assert( fromacnt.balance >= quantity, "overdrawn balance" );
         _accounts.modify( fromacnt, from, [&]( auto& a ){ a.balance -= quantity; } );

         add_balance( from, to, quantity );
      }

      // @abi action
      void issue( account_name to, asset quantity ) {
         require_auth( _self );
         eosio_assert( quantity.symbol == token_symbol, "wrong symbol" );

         add_balance( _self, to, quantity );
         add_total_supply(_self, quantity);
      }

   private:
      // @abi table
      struct account {
         account_name owner;
         eosio::asset balance;

         uint64_t primary_key()const { return owner; }
      };
      eosio::multi_index<N(account), account> _accounts;

      // @abi table
      struct state {
         uint64_t id;
         eosio::asset totalSupply;

         uint64_t primary_key()const { return id; }
      };
      eosio::multi_index<N(state), state> _state;


      void add_balance( account_name payer, account_name to, asset q ) {
         auto toitr = _accounts.find( to );
         if( toitr == _accounts.end() ) {
           _accounts.emplace( payer, [&]( auto& a ) {
              a.owner = to;
              a.balance = q;
           });
         } else {
           _accounts.modify( toitr, 0, [&]( auto& a ) {
              a.balance += q;
              eosio_assert( a.balance >= q, "overflow detected" );
           });
         }
      }

      void add_total_supply(account_name payer, asset cnt ) {
         auto toitr = _state.find( 0 );
         if( toitr == _state.end() ) {
           _state.emplace( payer, [&]( auto& a ) {
              a.id = 0;
              a.totalSupply = cnt;
           });
         } else {
           _state.modify( toitr, 0, [&]( auto& a ) {
              a.totalSupply += cnt;
              eosio_assert( a.totalSupply >= cnt, "overflow detected" );
           });
         }
      }
};

EOSIO_ABI( simpletoken, (transfer)(issue))


    """
